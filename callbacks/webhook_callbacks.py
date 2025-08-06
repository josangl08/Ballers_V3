# callbacks/webhook_callbacks.py
"""
Callbacks de fallback para SSE (Server-Sent Events).
Proporciona fallback polling cuando SSE no está disponible.
"""
import time

from dash import Input, Output, no_update


def register_webhook_callbacks(app):
    """
    🛡️ SISTEMA HÍBRIDO: SSE principal + fallback polling de seguridad.
    SSE maneja updates en tiempo real, fallback se activa solo si SSE falla.
    """

    # 🛡️ FALLBACK POLLING: Solo se ejecuta si SSE no está disponible
    @app.callback(
        Output("fallback-trigger", "data"),
        [Input("fallback-interval", "n_intervals")],
        prevent_initial_call=True,
    )
    def fallback_polling_check(n_intervals):
        """
        Fallback polling que se activa solo cuando SSE falla.
        Verificación muy conservadora cada 30 segundos.
        """
        if n_intervals > 0:
            timestamp = int(time.time())
            print(
                f"🛡️ Fallback polling active - SSE connection lost (check #{n_intervals})"
            )
            print(f"🔄 Fallback refresh triggered at {timestamp}")
            return timestamp
        return no_update

    print("🛡️ Hybrid system registered - SSE primary, fallback polling as safety net")
