from __future__ import annotations

import datetime as dt
import json
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components

from config import CALENDAR_COLORS
from models import Session

HEX = {k: v["hex"] for k, v in CALENDAR_COLORS.items()}
TZ = ZoneInfo("Europe/Madrid")


def _fmt_local(ts: dt.datetime) -> str:
    """Devuelve 'YYYY-MM-DDTHH:MM:SS' sin zona."""
    return ts.strftime("%Y-%m-%dT%H:%M:%S")


def _to_event(s: Session) -> dict:
    return {
        "id": s.id,
        "title": f"{s.coach.user.name} × {s.player.user.name}",
        "start": _fmt_local(s.start_time),  # 13:00 «tal cual»
        "end": _fmt_local(s.end_time) if s.end_time else "",
        "description": s.notes or "",
        "player": s.player.user.name,
        "coach": s.coach.user.name,
        "color": HEX[s.status.value],
    }


def show_calendar(
    title: str,
    sessions,
    *,
    height: int = 650,
    editable: bool = False,
    key: str = "calendar",
) -> None:

    st.subheader(title)
    events = json.dumps([_to_event(s) for s in sessions], default=str)
    html = f"""
<link  href="https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.js"></script>

<div id="{key}"></div>

<script>
document.addEventListener("DOMContentLoaded", () => {{
  const root = document.getElementById("{key}");
  if (root.firstChild) return;                 // evita redibujar
  console.log("⚽ FullCalendar: mounting…");

  try {{
    const cal = new FullCalendar.Calendar(root, {{
        initialView: "dayGridMonth",
        headerToolbar: {{
            left:   "prev,next today",
            center: "title",
            right:  "dayGridMonth,timeGridWeek,timeGridDay,listWeek"
        }},
        slotEventOverlap: false,   // NO permite que dos eventos solapen la ranura
        eventOverlap:     false,   // idem para overlaps parciales
        locale:  "en",
        timeZone:"local",
        height:  {height},
        slotMinTime: "08:00:00",
        slotMaxTime: "19:00:00",
        firstDay: 1,
        navLinks: true,
        editable: {str(editable).lower()},

        /* Formato 24 h para todas las vistas */
        eventTimeFormat: {{hour:'2-digit', minute:'2-digit', hourCycle:'h23'}},
        slotLabelFormat: {{hour:'2-digit', minute:'2-digit', hourCycle:'h23'}},
        listDayFormat:   {{weekday:'long', day:'numeric', month:'long'}},
        events:  {events},

        eventDidMount: ({{
            event: ev, el
        }}) => {{
        /* — tooltip — */
        const f = new Intl.DateTimeFormat("en-GB",{{ hour:'2-digit', minute:'2-digit', hourCycle:'h23'}});
        let html = `<span style=\"color:rgba(36,222,132,1)\"><strong>${{f.format(ev.start)}}–${{f.format(ev.end)}}</strong></span><br>
                    <span style=\"color:rgba(36,222,132,1)\">Player:</span> ${{ev.extendedProps.player}}<br>
                    <span style=\"color:rgba(36,222,132,1)\">Coach:</span> ${{ev.extendedProps.coach}}`;
        if (ev.extendedProps.description) html += `<br>${{ev.extendedProps.description}}`;

        const tip = Object.assign(document.createElement("div"), {{
          className: "fc-tip",
          innerHTML: html,
          style: `
            position:absolute; z-index:10001; background:#333; color:#fff;
            padding:8px; border:1px solid #555; border-radius:6px;
          `
        }});
        tip.hidden = true;

        el.addEventListener("mouseenter", () => {{
          tip.hidden = false; document.body.appendChild(tip);
        }});
        el.addEventListener("mouseleave", () => {{
          tip.hidden = true; if (document.body.contains(tip)) document.body.removeChild(tip);
        }});
        el.addEventListener("mousemove", e => {{
          tip.style.top  = e.pageY + "px";
          tip.style.left = e.pageX + "px";
        }});
      }}
    }});
    cal.render();
  }} catch (e) {{
    console.error("⚽ FullCalendar error →", e);
  }}
}});
</script>

<style>

/* FONDO TRANSPARENTE Y LINEAS SUAVES ------------------------------------*/
#{key} .fc-scrollgrid,
#{key} th,
#{key} td        {{ border-color:rgba(128,128,128,0.15); background:transparent; }}

/* CABECERA días -----------------------------------------------------------*/
#{key} .fc-col-header-cell         {{ background:#333; color:#FAFAFA; border-bottom: 1px solid rgba(128,128,128,0.3); }}
#{key} .fc-toolbar-title           {{ color:#FAFAFA; }}

/* FONDO DEL CALENDARIO TRANSPARENTE ------------------------------------*/
#{key} .fc-view-harness            {{ background:transparent; }}
#{key} .fc                         {{ background:transparent; }}

/* BOTONES -----------------------------------------------------------------*/
#{key} .fc-button-primary,
#{key} .fc-button-primary:disabled {{background:#333; border:#333; color:rgba(36,222,132,1);    }}
#{key} .fc-button-primary:not(:disabled):hover,
#{key} .fc-button-primary:not(:disabled).fc-button-active {{background:#1DDD6E; border:#1DDD6E; color:#333; }}

/* HOY y eventos pasados ---------------------------------------------------*/
#{key} .fc-day-today {{ background:rgba(29,221,110,.1); }}
#{key} .fc-event-past {{ opacity:.4; }}

/* MES - TRANSPARENTE CON LÍNEAS SUAVES ------------------------------------*/
#{key} .fc-daygrid-event,
#{key} .fc-daygrid-event-dot           {{ color:#FAFAFA;   }}
#{key} .fc-daygrid-day-frame           {{ background:rgba(255,255,255,0.05); border-color:rgba(128,128,128,0.15); }}
#{key} .fc-daygrid-day-number          {{ background:transparent; color:#FAFAFA; }}
#{key} .fc-daygrid-event-harness       {{ background: rgba(51,51,51,0.8); border: 1px solid rgba(128,128,128,0.4); margin: 2px; border-radius: 6px; }}
#{key} .fc-daygrid-event               {{ margin: 0; border-radius: 6px; background:transparent; }}
#{key} .fc-daygrid-event:hover         {{ background: rgba(36,222,132,0.8) !important; border-color: rgba(36,222,132,1) !important; }}

/* SEMANA / DÍA ------------------------------------------------------------*/
#{key} .fc-timegrid-slot-label-cushion,
#{key} .fc-timegrid-axis-frame,
#{key} .fc-scrollgrid-sync-inner       {{ color:#FAFAFA;   }}
#{key} .fc-daygrid-day-events          {{ margin: 1px; }}
#{key} .fc-timegrid-event:hover {{background: rgba(36,222,132,0.9) !important; border-color: rgba(36,222,132,1) !important; }}
#{key} .fc-timegrid-event-harness {{margin: 1.5px;  }}

/* LISTA - TRANSPARENTE CON LÍNEAS SUAVES ---------------------------------*/
#{key} .fc-list,
#{key} .fc-list-day-cushion            {{ background:transparent; color:#FAFAFA; border-bottom: 1px solid rgba(128,128,128,0.15); }}
#{key} .fc-list-event                  {{ background:transparent; color:#FAFAFA; border:1px solid rgba(128,128,128,0.15); }}
#{key} .fc-list-event:hover td         {{ background: rgba(36,222,132,0.2) !important; color: #FAFAFA !important; }}
#{key} .fc-list-event:hover a          {{ color: #24DE84 !important; }}
</style>
"""
    components.html(html, height=height + 70, scrolling=False)


def show_calendar_dash(
    sessions,
    *,
    height: int = 650,
    editable: bool = False,
    key: str = "dash-calendar",
) -> str:
    """
    Versión para Dash del calendario.
    Reutiliza toda la lógica de show_calendar() pero retorna HTML string.
    """
    from dash import html

    events = json.dumps([_to_event(s) for s in sessions], default=str)

    # Reutilizar exactamente el mismo HTML que la versión Streamlit
    calendar_html = f"""
<link  href="https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.js"></script>

<div id="{key}"></div>

<script>
document.addEventListener("DOMContentLoaded", () => {{
  const root = document.getElementById("{key}");

  // Recuperar vista guardada o usar vista por defecto
  let currentView = localStorage.getItem('calendar-view') || "dayGridMonth";

  if (root.firstChild) {{
    // Limpiar calendario anterior para reactividad en Dash
    root.innerHTML = '';
  }}
  console.log("FullCalendar Dash: mounting...");

  try {{
    const cal = new FullCalendar.Calendar(root, {{
        initialView: currentView,
        headerToolbar: {{
            left:   "prev,next today",
            center: "title",
            right:  "dayGridMonth,timeGridWeek,timeGridDay,listWeek"
        }},
        slotEventOverlap: false,   // NO permite que dos eventos solapen la ranura
        eventOverlap:     false,   // idem para overlaps parciales
        locale:  "en",
        timeZone:"local",
        height:  {height},
        slotMinTime: "08:00:00",
        slotMaxTime: "19:00:00",
        firstDay: 1,
        navLinks: true,
        editable: {str(editable).lower()},

        // Guardar vista actual cuando cambia
        viewDidMount: function(view) {{
            localStorage.setItem('calendar-view', view.view.type);
        }},

        /* Formato 24 h para todas las vistas */
        eventTimeFormat: {{hour:'2-digit', minute:'2-digit', hourCycle:'h23'}},
        slotLabelFormat: {{hour:'2-digit', minute:'2-digit', hourCycle:'h23'}},
        listDayFormat:   {{weekday:'long', day:'numeric', month:'long'}},
        events:  {events},

        eventDidMount: ({{
            event: ev, el
        }}) => {{
        /* — tooltip — */
        const f = new Intl.DateTimeFormat("en-GB",{{ hour:'2-digit', minute:'2-digit', hourCycle:'h23'}});
        let html = `<span style="color:rgba(36,222,132,1)"><strong>${{f.format(ev.start)}}–${{f.format(ev.end)}}</strong></span><br>
                    <span style="color:rgba(36,222,132,1)">Player:</span> ${{ev.extendedProps.player}}<br>
                    <span style="color:rgba(36,222,132,1)">Coach:</span> ${{ev.extendedProps.coach}}`;
        if (ev.extendedProps.description) html += `<br>${{ev.extendedProps.description}}`;

        const tip = Object.assign(document.createElement("div"), {{
          className: "fc-tip",
          innerHTML: html,
          style: `
            position:absolute; z-index:10001; background:#333; color:#fff;
            padding:8px; border:1px solid #555; border-radius:6px;
          `
        }});
        tip.hidden = true;

        el.addEventListener("mouseenter", () => {{
          tip.hidden = false; document.body.appendChild(tip);
        }});
        el.addEventListener("mouseleave", () => {{
          tip.hidden = true; if (document.body.contains(tip)) document.body.removeChild(tip);
        }});
        el.addEventListener("mousemove", e => {{
          tip.style.top  = e.pageY + "px";
          tip.style.left = e.pageX + "px";
        }});
      }}
    }});
    cal.render();
  }} catch (e) {{
    console.error("FullCalendar Dash error:", e);
  }}
}});
</script>

<style>

/* FONDO TRANSPARENTE Y LINEAS SUAVES ------------------------------------*/
#{key} .fc-scrollgrid,
#{key} th,
#{key} td        {{ border-color:rgba(128,128,128,0.15); background:transparent; }}

/* CABECERA días -----------------------------------------------------------*/
#{key} .fc-col-header-cell         {{ background:#333; color:#FAFAFA; border-bottom: 1px solid rgba(128,128,128,0.3); }}
#{key} .fc-toolbar-title           {{ color:#FAFAFA; }}

/* FONDO DEL CALENDARIO TRANSPARENTE ------------------------------------*/
#{key} .fc-view-harness            {{ background:transparent; }}
#{key} .fc                         {{ background:transparent; }}

/* BOTONES -----------------------------------------------------------------*/
#{key} .fc-button-primary,
#{key} .fc-button-primary:disabled {{background:#333; border:#333; color:rgba(36,222,132,1);    }}
#{key} .fc-button-primary:not(:disabled):hover,
#{key} .fc-button-primary:not(:disabled).fc-button-active {{background:#1DDD6E; border:#1DDD6E; color:#333; }}

/* HOY y eventos pasados ---------------------------------------------------*/
#{key} .fc-day-today {{ background:rgba(29,221,110,.1); }}
#{key} .fc-event-past {{ opacity:.4; }}

/* MES - TRANSPARENTE CON LÍNEAS SUAVES ------------------------------------*/
#{key} .fc-daygrid-event,
#{key} .fc-daygrid-event-dot           {{ color:#FAFAFA;   }}
#{key} .fc-daygrid-day-frame           {{ background:rgba(255,255,255,0.05); border-color:rgba(128,128,128,0.15); }}
#{key} .fc-daygrid-day-number          {{ background:transparent; color:#FAFAFA; }}
#{key} .fc-daygrid-event-harness       {{ background: rgba(51,51,51,0.8); border: 1px solid rgba(128,128,128,0.4); margin: 2px; border-radius: 6px; }}
#{key} .fc-daygrid-event               {{ margin: 0; border-radius: 6px; background:transparent; }}
#{key} .fc-daygrid-event:hover         {{ background: rgba(36,222,132,0.8) !important; border-color: rgba(36,222,132,1) !important; }}

/* SEMANA - TRANSPARENTE CON LÍNEAS SUAVES --------------------------------*/
#{key} .fc-timegrid-divider,
#{key} .fc-timegrid-slot-lane          {{ border-color:rgba(128,128,128,0.15); background:transparent; color:#FAFAFA; }}
#{key} .fc-timegrid-slot-label-cushion,
#{key} .fc-timegrid-axis-frame,
#{key} .fc-scrollgrid-sync-inner       {{ color:#FAFAFA; background:transparent; }}
#{key} .fc-timegrid-event              {{ background: rgba(51,51,51,0.8) !important; border: 1px solid rgba(128,128,128,0.4) !important; border-radius: 6px; }}
#{key} .fc-timegrid-event:hover        {{ background: rgba(36,222,132,0.8) !important; border-color: rgba(36,222,132,1) !important; }}
#{key} .fc-timegrid-event-harness      {{ margin: 1.5px; }}

/* LISTA - TRANSPARENTE CON LÍNEAS SUAVES ---------------------------------*/
#{key} .fc-list,
#{key} .fc-list-day-cushion            {{ background:transparent; color:#FAFAFA; border-bottom: 1px solid rgba(128,128,128,0.15); }}
#{key} .fc-list-event                  {{ background:transparent; color:#FAFAFA; border:1px solid rgba(128,128,128,0.15); }}
#{key} .fc-list-event:hover td         {{ background: rgba(36,222,132,0.2) !important; color: #FAFAFA !important; }}
#{key} .fc-list-event:hover a          {{ color: #24DE84 !important; }}
</style>
"""

    return html.Div(
        html.Iframe(
            srcDoc=calendar_html,
            style={
                "width": "100%",
                "height": f"{height + 70}px",
                "border": "none",
                "background-color": "transparent",
            },
        )
    )
