# 🔐 Credenciales para Testing - Ballers Dash App

## 🚀 URL de la Aplicación
- **Local**: http://127.0.0.1:8050/

## 👤 Credenciales de Prueba

### 👨‍💼 Administradores
```
Usuario: admin
Contraseña: admin
Nombre: Miguel Ramirez
```

### 🏃‍♂️ Entrenadores
```
Usuario: coach1
Contraseña: coach123
Nombre: Sara Johnson
```

### ⚽ Jugadores
```
Usuario: player1
Contraseña: player123
Nombre: Joseph Boyd
```

## 🧪 Flujo de Testing Recomendado

### 1. **Test de Login**
- [ ] Acceder a http://127.0.0.1:8050/
- [ ] Probar login con credenciales válidas
- [ ] Verificar redirección a dashboard
- [ ] Probar login con credenciales inválidas

### 2. **Test de Dashboard por Rol**
- [ ] **Admin**: Verificar panel de administración con botones de gestión
- [ ] **Coach**: Verificar panel de entrenador con sesiones y calendario
- [ ] **Player**: Verificar panel de jugador con calendario y perfil

### 3. **Test de Navegación**
- [ ] Verificar navegación entre páginas
- [ ] Probar logout
- [ ] Verificar redirección a login después de logout

### 4. **Test de UI/UX**
- [ ] Verificar diseño responsive
- [ ] Verificar alertas de éxito/error
- [ ] Verificar que la navegación sea específica por rol

## 🐛 Problemas Conocidos
- Las páginas secundarias (Users, Sessions, etc.) muestran "En construcción" - esto es esperado
- El mensaje de Homebrew es solo ruido en la consola, no afecta la funcionalidad
