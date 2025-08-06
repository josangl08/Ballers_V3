# controllers/export_controller.py
"""
Controlador para exportación de reportes en PDF.
Maneja la lógica de generación de PDFs para perfiles, sesiones y finanzas.
"""
import calendar
import datetime as dt
import io
import os
from typing import List, Optional, Tuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import joinedload

from controllers.db import get_db_session
from controllers.player_controller import get_player_profile_data
from controllers.sheets_controller_dash import get_accounting_df_dash
from models import Coach, Player, Session, SessionStatus, TestResult


class ExportController:
    """
    Controlador para exportación de reportes.
    Genera PDFs con datos de jugadores, sesiones y finanzas.
    """

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configura estilos personalizados para los reportes."""
        # Título principal
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=18,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#1E88E5"),
            )
        )

        # Subtítulo
        self.styles.add(
            ParagraphStyle(
                name="CustomSubtitle",
                parent=self.styles["Heading2"],
                fontSize=14,
                spaceAfter=20,
                textColor=colors.HexColor("#0D47A1"),
            )
        )

        # Texto normal
        self.styles.add(
            ParagraphStyle(
                name="CustomNormal",
                parent=self.styles["Normal"],
                fontSize=10,
                spaceAfter=12,
            )
        )

    def generate_player_report(
        self,
        player_id: int,
        start_date: dt.date,
        end_date: dt.date,
        status_filter: List[str],
        selected_metrics: List[str],
    ) -> Tuple[io.BytesIO, str]:
        """
        Genera reporte PDF de un jugador.

        Args:
            player_id: ID del jugador
            start_date: Fecha inicio del filtro
            end_date: Fecha fin del filtro
            status_filter: Estados de sesión a incluir
            selected_metrics: Métricas seleccionadas para el gráfico

        Returns:
            Tuple (PDF buffer, filename)
        """
        # Obtener datos del jugador
        profile_data = get_player_profile_data(player_id=player_id)
        if not profile_data:
            raise ValueError("Player not found")

        player = profile_data["player"]
        user = profile_data["user"]
        stats = profile_data["stats"]
        test_results = profile_data["test_results"]

        # Obtener sesiones filtradas con eager loading
        db = get_db_session()
        try:

            sessions_query = (
                db.query(Session)
                .options(
                    joinedload(Session.coach).joinedload(Coach.user),
                    joinedload(Session.player).joinedload(Player.user),
                )
                .filter(
                    Session.player_id == player.player_id,
                    Session.start_time >= dt.datetime.combine(start_date, dt.time.min),
                    Session.start_time <= dt.datetime.combine(end_date, dt.time.max),
                )
            )

            if status_filter:
                status_enums = [SessionStatus(s) for s in status_filter]
                sessions_query = sessions_query.filter(Session.status.in_(status_enums))

            sessions = sessions_query.order_by(Session.start_time.asc()).all()

        finally:
            db.close()

        # Crear PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        story = []

        # Título
        title = Paragraph(f"Player Report: {user.name}", self.styles["CustomTitle"])
        story.append(title)
        story.append(Spacer(1, 20))

        # Información personal con foto
        story.append(Paragraph("Personal Information", self.styles["CustomSubtitle"]))

        # Intentar añadir la foto
        photo_cell = ""
        try:
            if user.profile_photo and os.path.exists(user.profile_photo):
                photo_image = Image(
                    user.profile_photo, width=1.5 * inch, height=1.5 * inch
                )
                photo_cell = photo_image
            else:
                photo_cell = Paragraph(
                    "No photo available", self.styles["CustomNormal"]
                )
        except Exception:
            photo_cell = Paragraph("Photo not available", self.styles["CustomNormal"])

        # Datos personales en formato de texto
        personal_info_text = f"""
        <b>Name:</b> {user.name}<br/>
        <b>Email:</b> {user.email}<br/>
        <b>Phone:</b> {user.phone or 'Not provided'}<br/>
        <b>LINE:</b> {user.line or 'Not provided'}<br/>
        <b>Age:</b> {f"{stats['age']} years" if stats['age'] else 'Not provided'}<br/>
        <b>Service:</b> {player.service}<br/>
        <b>Enrollment Sessions:</b> {player.enrolment}<br/>
        <b>Next Session:</b> {stats['next_session']}
        """

        personal_info_paragraph = Paragraph(
            personal_info_text, self.styles["CustomNormal"]
        )

        # Crear tabla con foto y datos lado a lado
        personal_table = Table(
            [[photo_cell, personal_info_paragraph]], colWidths=[2 * inch, 4 * inch]
        )
        personal_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(personal_table)
        story.append(Spacer(1, 20))

        # Métricas de sesiones
        story.append(Paragraph("Session Metrics", self.styles["CustomSubtitle"]))

        metrics_data = [
            ["Completed", "Scheduled", "Remaining"],
            [str(stats["completed"]), str(stats["scheduled"]), str(stats["remaining"])],
        ]

        metrics_table = Table(metrics_data, colWidths=[2 * inch, 2 * inch, 2 * inch])
        metrics_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4CAF50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(metrics_table)
        story.append(Spacer(1, 20))

        # Calendario simulado
        if sessions:
            story.append(
                Paragraph(
                    f"Calendar View ({start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')})",
                    self.styles["CustomSubtitle"],
                )
            )

            calendar_table = self._create_calendar_simulation_table(
                sessions, start_date, end_date
            )
            story.append(calendar_table)
            story.append(Spacer(1, 20))

        # Tabla de sesiones
        if sessions:
            story.append(
                Paragraph(
                    f"Sessions ({start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')})",
                    self.styles["CustomSubtitle"],
                )
            )

            sessions_data = [["ID", "Coach", "Date", "Time", "Status"]]
            for session in sessions:
                # Obtener nombre del coach (manejar snapshots)
                if session.coach_id and session.coach and session.coach.user:
                    coach_name = session.coach.user.name
                else:
                    coach_name = session.coach_name_snapshot or "Coach deleted"

                sessions_data.append(
                    [
                        str(session.id),
                        coach_name,
                        session.start_time.strftime("%d/%m/%Y"),
                        f"{session.start_time.strftime('%H:%M')}-{session.end_time.strftime('%H:%M')}",
                        session.status.value,
                    ]
                )

            sessions_table = Table(
                sessions_data,
                colWidths=[0.8 * inch, 2 * inch, 1.5 * inch, 1.5 * inch, 1.2 * inch],
            )
            sessions_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E88E5")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(sessions_table)
            story.append(Spacer(1, 20))

        # Gráfico de progresión de tests (si hay datos y métricas seleccionadas)
        if test_results and selected_metrics:
            story.append(
                Paragraph("Performance Evolution", self.styles["CustomSubtitle"])
            )

            # Crear gráfico con matplotlib
            chart_buffer = self._create_test_chart(
                test_results, selected_metrics, player.user.name
            )
            chart_image = Image(chart_buffer, width=6 * inch, height=4 * inch)
            story.append(chart_image)
            story.append(Spacer(1, 20))

        # Notas
        if player.notes:
            story.append(Paragraph("Notes", self.styles["CustomSubtitle"]))
            notes_text = Paragraph(player.notes, self.styles["CustomNormal"])
            story.append(notes_text)

        # Generar PDF
        doc.build(story)
        buffer.seek(0)

        # Generar nombre de archivo
        filename = f"{player.user.name.replace(' ', '_')}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"

        return buffer, filename

    def generate_sessions_report(
        self,
        start_date: dt.date,
        end_date: dt.date,
        coach_id: Optional[int] = None,
        status_filter: List[str] = [],
        user_type: str = "admin",
        user_name: str = "Sessions",
    ) -> Tuple[io.BytesIO, str]:
        """
        Genera reporte PDF de sesiones.

        Args:
            start_date: Fecha inicio
            end_date: Fecha fin
            coach_id: ID del coach (opcional)
            status_filter: Estados de sesión
            user_type: Tipo de usuario que genera el reporte
            user_name: Nombre del usuario/coach

        Returns:
            Tuple (PDF buffer, filename)
        """
        # Obtener sesiones con eager loading
        db = get_db_session()
        try:

            query = (
                db.query(Session)
                .options(
                    joinedload(Session.coach).joinedload(Coach.user),
                    joinedload(Session.player).joinedload(Player.user),
                )
                .filter(
                    Session.start_time >= dt.datetime.combine(start_date, dt.time.min),
                    Session.start_time <= dt.datetime.combine(end_date, dt.time.max),
                )
            )

            if coach_id:
                query = query.filter(Session.coach_id == coach_id)

            if status_filter:
                status_enums = [SessionStatus(s) for s in status_filter]
                query = query.filter(Session.status.in_(status_enums))

            sessions = query.order_by(Session.start_time.asc()).all()

        finally:
            db.close()

        # Crear PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        story = []

        # Título
        title_text = f"Sessions Report: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"
        if coach_id and user_type == "coach":
            title_text = f"Coach {user_name} - " + title_text

        title = Paragraph(title_text, self.styles["CustomTitle"])
        story.append(title)
        story.append(Spacer(1, 20))

        # Resumen
        total_sessions = len(sessions)
        completed = sum(1 for s in sessions if s.status == SessionStatus.COMPLETED)
        scheduled = sum(1 for s in sessions if s.status == SessionStatus.SCHEDULED)
        canceled = sum(1 for s in sessions if s.status == SessionStatus.CANCELED)

        summary_data = [
            ["Total Sessions", "Completed", "Scheduled", "Canceled"],
            [str(total_sessions), str(completed), str(scheduled), str(canceled)],
        ]

        summary_table = Table(
            summary_data, colWidths=[1.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch]
        )
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E88E5")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # Calendario simulado
        if sessions:
            story.append(Paragraph("Calendar View", self.styles["CustomSubtitle"]))

            calendar_table = self._create_calendar_simulation_table(
                sessions, start_date, end_date
            )
            story.append(calendar_table)
            story.append(Spacer(1, 20))

        # Tabla de sesiones
        if sessions:
            story.append(Paragraph("Sessions Details", self.styles["CustomSubtitle"]))

            sessions_data = [["ID", "Coach", "Player", "Date", "Time", "Status"]]
            for session in sessions:
                # Obtener nombres (manejar snapshots)
                if session.coach_id and session.coach and session.coach.user:
                    coach_name = session.coach.user.name
                else:
                    coach_name = session.coach_name_snapshot or "Coach deleted"

                if session.player_id and session.player and session.player.user:
                    player_name = session.player.user.name
                else:
                    player_name = session.player_name_snapshot or "Player deleted"

                sessions_data.append(
                    [
                        str(session.id),
                        coach_name,
                        player_name,
                        session.start_time.strftime("%d/%m/%Y"),
                        f"{session.start_time.strftime('%H:%M')}-{session.end_time.strftime('%H:%M')}",
                        session.status.value,
                    ]
                )

            sessions_table = Table(
                sessions_data,
                colWidths=[
                    0.6 * inch,
                    1.8 * inch,
                    1.8 * inch,
                    1.2 * inch,
                    1.2 * inch,
                    1 * inch,
                ],
            )
            sessions_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E88E5")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(sessions_table)
        else:
            story.append(
                Paragraph(
                    "No sessions found for the selected period.",
                    self.styles["CustomNormal"],
                )
            )

        # Generar PDF
        doc.build(story)
        buffer.seek(0)

        # Generar nombre de archivo
        if user_type == "coach":
            filename = f"{user_name.replace(' ', '_')}_Sessions_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
        else:
            filename = f"Sessions_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"

        return buffer, filename

    def generate_financials_report(
        self, start_date: dt.date, end_date: dt.date
    ) -> Tuple[io.BytesIO, str]:
        """
        Genera reporte PDF de finanzas.

        Args:
            start_date: Fecha inicio del filtro
            end_date: Fecha fin del filtro

        Returns:
            Tuple (PDF buffer, filename)
        """
        # Obtener datos financieros
        df, error_msg = get_accounting_df_dash()
        if error_msg:
            raise ValueError(f"Error obteniendo datos financieros: {error_msg}")
        df_no_total = df.iloc[:-1].copy()

        # Crear PDF en orientación horizontal
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        story = []

        # Título
        title = Paragraph(
            f"Financial Report ({start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')})",
            self.styles["CustomTitle"],
        )
        story.append(title)
        story.append(Spacer(1, 20))

        # Métricas resumen
        total_gastos = df_no_total["Gastos"].sum()
        total_ingresos = df_no_total["Ingresos"].sum()
        balance = total_ingresos - total_gastos

        metrics_data = [
            ["Total Income (€)", "Total Expenses (€)", "Balance (€)"],
            [f"{total_ingresos:,.2f}", f"{total_gastos:,.2f}", f"{balance:,.2f}"],
        ]

        metrics_table = Table(
            metrics_data, colWidths=[2.5 * inch, 2.5 * inch, 2.5 * inch]
        )
        metrics_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4CAF50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 14),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(metrics_table)
        story.append(Spacer(1, 20))

        # Tabla de movimientos financieros
        story.append(Paragraph("Financial Movements", self.styles["CustomSubtitle"]))

        # Convertir DataFrame a tabla para PDF
        financial_data = [df_no_total.columns.tolist()]
        for _, row in df_no_total.iterrows():
            # Formatear valores para mejor presentación
            formatted_row = []
            for i, val in enumerate(row.tolist()):
                if i == 0:  # Primera columna (fecha)
                    formatted_row.append(str(val))
                elif (
                    "Ingresos" in df_no_total.columns[i]
                    or "Gastos" in df_no_total.columns[i]
                ):
                    # Formatear números como moneda
                    try:
                        formatted_row.append(f"€{float(val):,.2f}")
                    except (ValueError, TypeError):
                        formatted_row.append(str(val))
                else:
                    formatted_row.append(str(val))
            financial_data.append(formatted_row)

        # Calcular anchos de columna basado en el contenido máximo
        def calculate_column_widths(data, available_width=10 * inch):
            """Calcula anchos óptimos basado en el contenido de cada columna"""
            if not data:
                return []

            num_cols = len(data[0])
            max_lengths = [0] * num_cols

            # Encontrar la longitud máxima en cada columna
            for row in data:
                for i, cell in enumerate(row):
                    max_lengths[i] = max(max_lengths[i], len(str(cell)))

            # Convertir longitudes a anchos proporcionales
            total_chars = sum(max_lengths)
            if total_chars == 0:
                return [available_width / num_cols] * num_cols

            col_widths = []
            for length in max_lengths:
                # Mínimo 0.8 inch por columna, máximo proporcional
                min_width = 0.8 * inch
                prop_width = (length / total_chars) * available_width
                col_widths.append(max(min_width, prop_width))

            # Ajustar si el total excede el ancho disponible
            total_width = sum(col_widths)
            if total_width > available_width:
                ratio = available_width / total_width
                col_widths = [w * ratio for w in col_widths]

            return col_widths

        col_widths = calculate_column_widths(financial_data)

        financial_table = Table(financial_data, colWidths=col_widths)
        financial_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E88E5")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    # Alternar colores de filas para mejor legibilidad
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F5F5F5")],
                    ),
                    # Ajustar texto para que no se superponga
                    ("WORDWRAP", (0, 0), (-1, -1), True),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(financial_table)
        story.append(Spacer(1, 20))

        # Gráfico de balance mensual
        story.append(
            Paragraph("Monthly Balance Evolution", self.styles["CustomSubtitle"])
        )

        # Crear gráfico de balance
        chart_buffer = self._create_financial_chart(df_no_total)
        chart_image = Image(chart_buffer, width=8 * inch, height=5 * inch)
        story.append(chart_image)

        # Generar PDF
        doc.build(story)
        buffer.seek(0)

        # Generar nombre de archivo
        filename = f"Financials_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"

        return buffer, filename

    def _create_test_chart(
        self,
        test_results: List[TestResult],
        selected_metrics: List[str],
        player_name: str,
    ) -> io.BytesIO:
        """Crea gráfico de evolución de tests usando matplotlib."""
        # Preparar datos
        dates = [test.date for test in reversed(test_results)]

        plt.figure(figsize=(10, 6))
        plt.style.use("default")

        # Mapeo de métricas
        metric_mapping = {
            "Ball Control": "ball_control",
            "Control & Passing": "control_pass",
            "Receiving & Passing/Scanning": "receive_scan",
            "Dribling & Ball Carriying": "dribling_carriying",
            "Shoot & Finishing": "shooting",
            "Crossbar": "crossbar",
            "Sprint": "sprint",
            "T-test": "t_test",
            "Jumping": "jumping",
        }

        colors_list = [
            "#1E88E5",
            "#4CAF50",
            "#FF9800",
            "#F44336",
            "#9C27B0",
            "#00BCD4",
            "#8BC34A",
            "#FFC107",
            "#795548",
        ]

        for i, metric in enumerate(selected_metrics):
            if metric in metric_mapping:
                attr_name = metric_mapping[metric]
                values = [
                    getattr(test, attr_name)
                    for test in reversed(test_results)
                    if getattr(test, attr_name) is not None
                ]
                valid_dates = [
                    dates[j]
                    for j, test in enumerate(reversed(test_results))
                    if getattr(test, attr_name) is not None
                ]

                if values:
                    color = colors_list[i % len(colors_list)]
                    # Convert dates to matplotlib dates
                    dates_num = mdates.date2num(valid_dates)
                    plt.plot(
                        dates_num,
                        values,
                        marker="o",
                        label=metric,
                        color=color,
                        linewidth=2,
                        markersize=6,
                    )

                    # Format x-axis to show dates properly
                    plt.gca().xaxis.set_major_formatter(
                        mdates.DateFormatter("%Y-%m-%d")
                    )

        plt.title(
            f"Performance Evolution - {player_name}", fontsize=14, fontweight="bold"
        )
        plt.xlabel("Date", fontsize=12)
        plt.ylabel("Score", fontsize=12)
        plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Guardar en buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
        buffer.seek(0)
        plt.close()

        return buffer

    def _create_calendar_simulation_table(
        self, sessions: List[Session], start_date: dt.date, end_date: dt.date
    ) -> Table:
        """
        Crea una tabla que simula la vista de calendario según el rango de fechas.
        """
        date_range_days = (end_date - start_date).days + 1

        if date_range_days == 1:
            return self._create_day_view_table(sessions, start_date)
        elif date_range_days <= 7:
            return self._create_week_view_table(sessions, start_date, end_date)
        elif date_range_days <= 31:
            return self._create_month_view_table(sessions, start_date, end_date)
        else:
            return self._create_extended_view_table(sessions, start_date, end_date)

    def _create_day_view_table(self, sessions: List[Session], date: dt.date) -> Table:
        """Crea tabla tipo día: horarios como filas, una columna del día."""
        day_sessions = [s for s in sessions if s.start_time.date() == date]

        # Crear horarios de 8:00 a 19:00
        hours = [dt.time(h, 0) for h in range(8, 20)]

        data = [["Time", f'{date.strftime("%d/%m/%Y")}']]

        for hour in hours:
            hour_str = hour.strftime("%H:%M")
            session_text = ""

            # Buscar sesiones en esta hora
            for session in day_sessions:
                session_start = session.start_time.time()
                session_end = (
                    session.end_time.time() if session.end_time else session_start
                )

                if session_start <= hour < session_end:
                    # Obtener nombres (manejar snapshots)
                    if session.coach_id and session.coach and session.coach.user:
                        coach_name = session.coach.user.name
                    else:
                        coach_name = session.coach_name_snapshot or "Coach deleted"

                    if session.player_id and session.player and session.player.user:
                        player_name = session.player.user.name
                    else:
                        player_name = session.player_name_snapshot or "Player deleted"

                    session_text = f"{coach_name} × {player_name}"
                    break

            data.append([hour_str, session_text])

        table = Table(data, colWidths=[1 * inch, 4 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E88E5")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        return table

    def _create_financial_chart(self, df_no_total: pd.DataFrame) -> io.BytesIO:
        """Crea gráfico de balance financiero usando matplotlib."""
        # Preparar datos mensuales
        fecha_col = df_no_total.columns[0]
        df_copy = df_no_total.copy()
        df_copy[fecha_col] = pd.to_datetime(df_copy[fecha_col], errors="coerce")
        df_copy["Mes"] = df_copy[fecha_col].dt.to_period("M").astype(str)

        monthly_summary = (
            df_copy.groupby("Mes")
            .agg({"Ingresos": "sum", "Gastos": "sum"})
            .reset_index()
        )

        monthly_summary["Balance mensual"] = (
            monthly_summary["Ingresos"] - monthly_summary["Gastos"]
        )
        monthly_summary["Balance acumulado"] = monthly_summary[
            "Balance mensual"
        ].cumsum()

        plt.figure(figsize=(12, 6))
        plt.style.use("default")

        # Crear gráfico de línea
        plt.plot(
            monthly_summary["Mes"],
            monthly_summary["Balance acumulado"],
            marker="o",
            color="#1E88E5",
            linewidth=3,
            markersize=8,
        )

        plt.title("Cumulative Balance Evolution", fontsize=14, fontweight="bold")
        plt.xlabel("Month", fontsize=12)
        plt.ylabel("Balance (€)", fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)

        # Formatear eje Y con euros
        ax = plt.gca()
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"€{x:,.0f}"))

        plt.tight_layout()

        # Guardar en buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
        buffer.seek(0)
        plt.close()

        return buffer

    def _create_week_view_table(
        self, sessions: List[Session], start_date: dt.date, end_date: dt.date
    ) -> Table:
        """Crea tabla tipo semana: días como columnas, horarios como filas."""
        # Generar lista de días
        current_date = start_date
        days = []
        while current_date <= end_date:
            days.append(current_date)
            current_date += dt.timedelta(days=1)

        # Crear horarios de 8:00 a 19:00
        hours = [dt.time(h, 0) for h in range(8, 20)]

        # Cabecera con días
        header = ["Time"] + [day.strftime("%d/%m") for day in days]
        data = [header]

        # Filas con horarios
        for hour in hours:
            hour_str = hour.strftime("%H:%M")
            row = [hour_str]

            for day in days:
                session_text = ""
                # Buscar sesiones en este día y hora
                for session in sessions:
                    if (
                        session.start_time.date() == day
                        and session.start_time.time()
                        <= hour
                        < (
                            session.end_time.time()
                            if session.end_time
                            else session.start_time.time()
                        )
                    ):
                        # Obtener nombres (manejar snapshots)
                        if session.coach_id and session.coach and session.coach.user:
                            coach_name = session.coach.user.name[:8]
                        else:
                            coach_name = (
                                session.coach_name_snapshot or "Coach deleted"
                            )[:8]

                        if session.player_id and session.player and session.player.user:
                            player_name = session.player.user.name[:8]
                        else:
                            player_name = (
                                session.player_name_snapshot or "Player deleted"
                            )[:8]

                        session_text = f"{coach_name}×{player_name}"
                        break
                row.append(session_text)

            data.append(row)

        # Calcular anchos de columna
        num_days = len(days)
        time_col_width = 0.8 * inch
        day_col_width = (6 * inch) / num_days if num_days > 0 else 1 * inch
        col_widths = [time_col_width] + [day_col_width] * num_days

        table = Table(data, colWidths=col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E88E5")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        return table

    def _create_month_view_table(
        self, sessions: List[Session], start_date: dt.date, end_date: dt.date
    ) -> Table:
        """Crea tabla tipo mes: calendario con días en celdas."""

        # Usar el mes de start_date como referencia
        year = start_date.year
        month = start_date.month

        # Obtener calendario del mes
        cal = calendar.monthcalendar(year, month)

        # Cabecera con días de la semana
        header = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        data = [header]

        # Procesar cada semana
        for week in cal:
            week_row = []
            for day in week:
                if day == 0:
                    week_row.append("")
                else:
                    day_date = dt.date(year, month, day)
                    cell_text = str(day)

                    # Agregar sesiones de ese día
                    day_sessions = [
                        s for s in sessions if s.start_time.date() == day_date
                    ]
                    if day_sessions:
                        session_count = len(day_sessions)
                        cell_text += f"\n({session_count} sessions)"

                    week_row.append(cell_text)

            data.append(week_row)

        table = Table(data, colWidths=[1 * inch] * 7)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E88E5")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

        return table

    def _create_extended_view_table(
        self, sessions: List[Session], start_date: dt.date, end_date: dt.date
    ) -> Table:
        """Crea tabla resumen para períodos largos."""
        # Agrupar sesiones por día
        sessions_by_day = {}
        for session in sessions:
            day = session.start_time.date()
            if day not in sessions_by_day:
                sessions_by_day[day] = []
            sessions_by_day[day].append(session)

        # Crear tabla con días que tienen sesiones
        data = [["Date", "Sessions Count", "Details"]]

        current_date = start_date
        while current_date <= end_date:
            if current_date in sessions_by_day:
                day_sessions = sessions_by_day[current_date]
                count = len(day_sessions)
                details = f"{count} sessions scheduled"
                data.append([current_date.strftime("%d/%m/%Y"), str(count), details])
            current_date += dt.timedelta(days=1)

        table = Table(data, colWidths=[1.5 * inch, 1.5 * inch, 3 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E88E5")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        return table


# Funciones de conveniencia
def generate_player_pdf(
    player_id: int,
    start_date: dt.date,
    end_date: dt.date,
    status_filter: List[str],
    selected_metrics: List[str],
) -> Tuple[io.BytesIO, str]:
    """Función de conveniencia para generar PDF de jugador."""
    controller = ExportController()
    return controller.generate_player_report(
        player_id, start_date, end_date, status_filter, selected_metrics
    )


def generate_sessions_pdf(
    start_date: dt.date,
    end_date: dt.date,
    coach_id: Optional[int] = None,
    status_filter: List[str] = [],
    user_type: str = "admin",
    user_name: str = "Sessions",
) -> Tuple[io.BytesIO, str]:
    """Función de conveniencia para generar PDF de sesiones."""
    controller = ExportController()
    return controller.generate_sessions_report(
        start_date, end_date, coach_id, status_filter, user_type, user_name
    )


def generate_financials_pdf(
    start_date: dt.date, end_date: dt.date
) -> Tuple[io.BytesIO, str]:
    """Función de conveniencia para generar PDF de finanzas."""
    controller = ExportController()
    return controller.generate_financials_report(start_date, end_date)
