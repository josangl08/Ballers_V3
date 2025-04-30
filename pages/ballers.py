# pages/ballers.py
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, Player, Coach, TestResult, Base
from datetime import datetime

def get_db_session():
    """Crea y devuelve una sesión de SQLAlchemy."""
    engine = create_engine('sqlite:///ballers_app.db')
    Base.metadata.create_all(engine)  # Crea tablas si no existen
    Session = sessionmaker(bind=engine)
    return Session()

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
        st.error("No se encontró información del jugador.")
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
            st.write(f"**Teléfono:** {user.phone}")
        if user.line:
            st.write(f"**LINE:** {user.line}")
        if user.date_of_birth:
            edad = datetime.now().year - user.date_of_birth.year
            st.write(f"**Edad:** {edad} años")
        
        st.write(f"**Servicio:** {player.service}")
        st.write(f"**Sesiones inscritas:** {player.enrolment}")
    
    # Mostrar pestañas con información adicional
    tab1, tab2 = st.tabs(["Resultados de Pruebas", "Notas"])
    
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
                    "Fecha": test.date,
                    "Control de balón": test.ball_control,
                    "Control de pase": test.control_pass,
                    "Recepción y escaneo": test.receive_scan,
                    "Dribling y conducción": test.dribling_carriying,
                    "Tiro": test.shooting,
                    "Travesaño": test.crossbar,
                    "Sprint": test.sprint,
                    "T-test": test.t_test,
                    "Salto": test.jumping
                }
                test_data.append(test_dict)
            
            df = pd.DataFrame(test_data)
            
            # Mostrar gráfico de evolución
            st.subheader("Evolución de rendimiento")
            metrics = df.columns.tolist()[1:]  # Todas las columnas excepto la fecha
            selected_metrics = st.multiselect(
                "Selecciona métricas para visualizar", 
                options=metrics,
                default=metrics[:3]
            )
            
            if selected_metrics:
                fig = px.line(
                    df, 
                    x="Fecha", 
                    y=selected_metrics,
                    title="Evolución de métricas de rendimiento",
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar tabla de resultados
            st.subheader("Historial de pruebas")
            for i, test in enumerate(test_results):
                with st.expander(f"Prueba del {test.date.strftime('%d/%m/%Y')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Nombre de prueba:** {test.test_name}")
                        st.write(f"**Peso:** {test.weight} kg")
                        st.write(f"**Altura:** {test.height} cm")
                    with col2:
                        st.write(f"**Control de balón:** {test.ball_control}")
                        st.write(f"**Control de pase:** {test.control_pass}")
                        st.write(f"**Recepción y escaneo:** {test.receive_scan}")
                        st.write(f"**Dribling y conducción:** {test.dribling_carriying}")
                        st.write(f"**Tiro:** {test.shooting}")
                        st.write(f"**Travesaño:** {test.crossbar}")
                        st.write(f"**Sprint:** {test.sprint}")
                        st.write(f"**T-test:** {test.t_test}")
                        st.write(f"**Salto:** {test.jumping}")
        else:
            st.info("No hay resultados de pruebas disponibles.")
    
    with tab2:
        st.subheader("Notas")
        if player.notes:
            st.write(player.notes)
        else:
            st.info("No hay notas disponibles.")
            
        # Si el usuario es coach o admin, permitir añadir notas
        if st.session_state.get("user_type") in ["coach", "admin"]:
            new_note = st.text_area("Añadir/Editar notas:", value=player.notes or "")
            if st.button("Guardar notas"):
                player.notes = new_note
                db_session.commit()
                st.success("Notas guardadas correctamente")
                st.experimental_rerun()
    
    db_session.close()

def show_player_list():
    """Muestra una lista de jugadores para coaches y admins."""
    db_session = get_db_session()
    
    # Obtener todos los jugadores
    players = db_session.query(Player).join(User).filter(User.is_active == True).all()
    
    if not players:
        st.info("No hay jugadores registrados.")
        db_session.close()
        return
    
    # Mostrar listado de jugadores
    st.subheader("Jugadores")
    
    # Filtros
    search_name = st.text_input("Buscar por nombre:")
    
    # Filtrar jugadores
    filtered_players = players
    if search_name:
        filtered_players = [p for p in players if search_name.lower() in p.user.name.lower()]
    
    # Mostrar jugadores en tarjetas
    cols = st.columns(3)
    for i, player in enumerate(filtered_players):
        with cols[i % 3]:
            with st.container(border=True):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(player.user.profile_photo, width=100)
                with col2:
                    st.write(f"**{player.user.name}**")
                    st.write(f"Servicio: {player.service}")
                    st.write(f"Sesiones: {player.enrolment}")
                
                if st.button("Ver perfil", key=f"player_{player.player_id}"):
                    st.session_state["selected_player_id"] = player.player_id
                    st.experimental_rerun()
    
    db_session.close()

def show_content():
    """Función principal para mostrar el contenido de la sección Ballers."""
    st.title("Ballers - Perfiles")
    
    # Si es un jugador, mostrar su propio perfil
    if st.session_state.get("user_type") == "player":
        show_player_profile()
    
    # Si es coach o admin, mostrar lista de jugadores o perfil seleccionado
    elif st.session_state.get("user_type") in ["coach", "admin"]:
        if "selected_player_id" in st.session_state:
            # Botón para volver a la lista
            if st.button("← Volver a la lista"):
                del st.session_state["selected_player_id"]
                st.experimental_rerun()
            
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