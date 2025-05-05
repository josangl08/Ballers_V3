# pages/ballers.py
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, Player, Coach, TestResult, Base, Session
from datetime import datetime
from controllers.calendar_controller import embed_calendar, SessionStatus
from controllers.db import get_db_session


def show_player_profile(player_id=None):
    """Muestra el perfil de un jugador específico."""
    db_session = get_db_session()
    
    # Si no se especifica un jugador, usamos el del usuario actual
    if player_id is None and st.session_state.get("user_type") == "player":
        user_id = st.session_state.get("user_id")
        player = db_session.query(Player).join(User).filter(User.user_id == user_id).first()
    else:
        player = db_session.query(Player).filter(Player.player_id == player_id).first()
    
    if not player:
        st.error("No player information found.")
        db_session.close()
        return
    
    user = player.user
    
    # Mostrar información del perfil
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.image(user.profile_photo, width=200)
    
    with col2:
        st.title(f"{user.name}")
        st.write(f"**Email:** {user.email}")
        if user.phone:
            st.write(f"**Tel:** {user.phone}")
        if user.line:
            st.write(f"**LINE:** {user.line}")
        if player.user.date_of_birth:
            age = datetime.now().year - player.user.date_of_birth.year
            st.write(f"**Age:** {age} years")
        # Find next scheduled session
        next_session = db_session.query(Session).filter(
        Session.player_id == player.player_id,
        Session.status == SessionStatus.SCHEDULED,
        Session.start_time > datetime.now()
        ).order_by(Session.start_time).first()
        
        next_session_text = "To be confirmed"
        if next_session:
            next_session_text = next_session.start_time.strftime("%d/%m/%Y %H:%M")   
        
        st.write(f"**Services:** {player.service}")
        st.write(f"**Enrollment Sessions:** {player.enrolment}")
        st.write(f"**Next Session:** {next_session_text}")

    st.divider()

    # Calendario de sesiones
    total = len(player.sessions)
    done  = sum(s.status is SessionStatus.COMPLETED for s in player.sessions)
    left  = max(player.enrolment - done, 0)

    colA, colB, colC = st.columns(3)
    colA.metric("Completed", done)
    colB.metric("Scheduled", total - done - sum(s.status is SessionStatus.CANCELED for s in player.sessions))
    colC.metric("Remaining", left)
        
        
    # Mostrar calendario de sesiones
    embed_calendar(
        title="My Calendar", 
        filter_tag=f"#P{player.player_id}"
    )
    

    # Mostrar pestañas con información adicional
    tab1, tab2 = st.tabs(["Test Results", "Notes"])
    
    with tab1:
        # Obtener resultados de pruebas del jugador
        test_results = db_session.query(TestResult).filter(
            TestResult.player_id == player.player_id
        ).order_by(TestResult.date.desc()).all()
        
        if test_results:
            # Mostrar la evolución de las métricas en un gráfico
            import pandas as pd
            import plotly.express as px
            
            # Preparar datos para el gráfico
            test_data = []
            for test in test_results:
                test_dict = {
                    "Date": test.date,
                    "Ball Control": test.ball_control,
                    "Controll & Passing": test.control_pass,
                    "Receiving & Passing/Scanning": test.receive_scan,
                    "Dribling & Ball Carriying": test.dribling_carriying,
                    "Shoot & Finishing": test.shooting,
                    "Crosbar": test.crossbar,
                    "Sprint": test.sprint,
                    "T-test": test.t_test,
                    "Jumping": test.jumping
                }
                test_data.append(test_dict)
            
            df = pd.DataFrame(test_data)
            
            # Mostrar gráfico de evolución
            st.subheader("Performance Evolution")
            metrics = df.columns.tolist()[1:]  # Todas las columnas excepto la fecha
            selected_metrics = st.multiselect(
                "Select metrics for visualization", 
                options=metrics,
                default=metrics[:3]
            )
            
            if selected_metrics:
                fig = px.line(
                    df, 
                    x="Date", 
                    y=selected_metrics,
                    title="Evolution of performance metrics",
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar tabla de resultados
            st.subheader("History of Tests")
            for i, test in enumerate(test_results):
                with st.expander(f"Test of {test.date.strftime('%d/%m/%Y')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Test Name:** {test.test_name}")
                        st.write(f"**Weight:** {test.weight} kg")
                        st.write(f"**Hight:** {test.height} cm")
                    with col2:
                        st.write(f"**Ball Control:** {test.ball_control}")
                        st.write(f"**Controll & Passing:** {test.control_pass}")
                        st.write(f"**Receiving & Passing/Scanning:** {test.receive_scan}")
                        st.write(f"**Dribling & Ball Carriying:** {test.dribling_carriying}")
                        st.write(f"**Shoot & Finishing:** {test.shooting}")
                        st.write(f"**Crosbar:** {test.crossbar}")
                        st.write(f"**Sprint:** {test.sprint}")
                        st.write(f"**T-test:** {test.t_test}")
                        st.write(f"**Salto:** {test.jumping}")
        else:
            st.info("No test results available.")
    
    with tab2:
        st.subheader("Notes")
        if player.notes:
            st.write(player.notes)
        else:
            st.info("No notes available.")
            
        # Si el usuario es coach o admin, permitir añadir notas
        if st.session_state.get("user_type") in ["coach", "admin"]:
            new_note = st.text_area("Add/Edit notes:", value=player.notes or "")
            if st.button("Save notes"):
                player.notes = new_note
                db_session.commit()
                st.success("Notes saved correctly")
                st.rerun()
    
    db_session.close()

def show_player_list():
    """Muestra una lista de jugadores para coaches y admins."""
    db_session = get_db_session()
    
    # Obtener todos los jugadores
    players = db_session.query(Player).join(User).filter(User.is_active == True).all()
    
    if not players:
        st.info("No registered players.")
        db_session.close()
        return
    
  
    # Filtros
    search_name = st.text_input("Search Player by name:")
    
    # Filtrar jugadores
    filtered_players = players
    if search_name:
        filtered_players = [p for p in players if search_name.lower() in p.user.name.lower()]
    
    
    # Mostrar jugadores en tarjetas
    cols = st.columns(3)
    for i, player in enumerate(filtered_players):
        done  = sum(s.status is SessionStatus.COMPLETED for s in player.sessions)
        if player.user.date_of_birth:
            age = datetime.now().year - player.user.date_of_birth.year
        # Find next scheduled session
        next_session = db_session.query(Session).filter(
        Session.player_id == player.player_id,
        Session.status == SessionStatus.SCHEDULED,
        Session.start_time > datetime.now()
        ).order_by(Session.start_time).first()
        
        next_session_text = "To be confirmed"
        if next_session:
            next_session_text = next_session.start_time.strftime("%d/%m/%Y %H:%M")
        with cols[i % 3]:
            with st.container(border=True):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(player.user.profile_photo, width=100)
                with col2:
                    st.write(f"**{player.user.name}**")
                    
                    st.write(f"**Age:** {age} years")
                    st.write(f"**Service:** {player.service}")
                    st.write(f"**Sessions:** {player.enrolment}")
                    st.write(f"**Reamining:** {player.enrolment - done}")
                    st.write(f"**Next Session:** {next_session_text}")


                
                if st.button("View Profile", key=f"player_{player.player_id}"):
                    st.session_state["selected_player_id"] = player.player_id
                    st.rerun()
    
    db_session.close()

def show_content():
    """Función principal para mostrar el contenido de la sección Ballers."""
    st.markdown('<h3 class="section-title">Profiles</h3>', unsafe_allow_html=True)
    
    # Si es un jugador, mostrar su propio perfil
    if st.session_state.get("user_type") == "player":
        show_player_profile()
    
    # Si es coach o admin, mostrar lista de jugadores o perfil seleccionado
    elif st.session_state.get("user_type") in ["coach", "admin"]:
        if "selected_player_id" in st.session_state:
            # Botón para volver a la lista
            if st.button("← Back to list"):
                del st.session_state["selected_player_id"]
                st.rerun()
            
            # Mostrar perfil del jugador seleccionado
            show_player_profile(st.session_state["selected_player_id"])
        else:
            # Mostrar lista de jugadores
            show_player_list()

if __name__ == "__main__":
    # Para pruebas
    st.session_state["user_id"] = 1
    st.session_state["user_type"] = "admin"
    show_content()