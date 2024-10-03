#!/usr/bin/env python3
import gi
import subprocess
import os
from threading import Thread
from gi.repository import Gtk, GdkPixbuf, GLib, Gio

gi.require_version("Gtk", "4.0")

# Obtener el valor de la variable de entorno USER
user = os.getenv("USER")

# Definir BASE_DIR usando la variable obtenida
BASE_DIR = f"/var/home/{user}/.local/share/applications/bambu-control"
CONFIG_FILE = os.path.join(BASE_DIR, "update_config.conf")
SCRIPT_PATH = os.path.join(BASE_DIR, "update_script.sh")

# Constantes para la interfaz
WINDOW_WIDTH = 500
WINDOW_HEIGHT = 800
SMALL_IMAGE_SIZE = 200  # Tamaño pequeño de las imágenes
LOGO_IMAGE_SIZE = 100    # Tamaño del logo
PROGRESS_IMAGE_SIZE = 70  # Tamaño de la imagen de progreso
COMPLETE_IMAGE_SIZE = 70  # Tamaño de la imagen de completo
MARGIN = 20

def read_config():
    """Lee el archivo de configuración y retorna los valores."""
    config = {"AUTO_UPDATES_ENABLED": True, "CHECK_FREQUENCY": "daily", "EXTENSIONES_HABILITADAS": False}
    
    if os.path.isfile(CONFIG_FILE) and os.path.getsize(CONFIG_FILE) > 0:
        with open(CONFIG_FILE) as f:
            for line in f:
                line = line.strip()
                if "=" in line and line:
                    try:
                        key, value = line.split("=", 1)
                        key, value = key.strip(), value.strip()
                        if key == "AUTO_UPDATES_ENABLED":
                            config[key] = value.lower() == "true"
                        elif key == "CHECK_FREQUENCY":
                            config[key] = value
                        elif key == "EXTENSIONES_HABILITADAS":
                            config[key] = value.lower() == "true"
                    except ValueError:
                        print(f"Línea malformada en el archivo de configuración: {line}")
    else:
        print("Archivo de configuración no encontrado o vacío. Usando valores por defecto.")
    
    return config

def write_config(auto_updates_enabled=None, check_frequency=None, extensiones_habilitadas=None):
    """Escribe la configuración al archivo sin sobrescribir todo."""
    if not os.path.isfile(CONFIG_FILE) or os.path.getsize(CONFIG_FILE) == 0:
        with open(CONFIG_FILE, 'w') as f:
            f.write(f"AUTO_UPDATES_ENABLED={str(auto_updates_enabled).lower()}\n")
            f.write(f"CHECK_FREQUENCY={check_frequency}\n")
            f.write(f"EXTENSIONES_HABILITADAS={str(extensiones_habilitadas).lower()}\n")
        print("Archivo de configuración creado con valores por defecto.")
        return

    if auto_updates_enabled is not None:
        ejecutar_comando(f"sed -i 's/^AUTO_UPDATES_ENABLED=.*/AUTO_UPDATES_ENABLED={str(auto_updates_enabled).lower()}/' {CONFIG_FILE}")
    
    if check_frequency is not None:
        ejecutar_comando(f"sed -i 's/^CHECK_FREQUENCY=.*/CHECK_FREQUENCY={check_frequency}/' {CONFIG_FILE}")

    if extensiones_habilitadas is not None:
        ejecutar_comando(f"sed -i 's/^EXTENSIONES_HABILITADAS=.*/EXTENSIONES_HABILITADAS={str(extensiones_habilitadas).lower()}/' {CONFIG_FILE}")
    
    print(f"Configuración guardada: AUTO_UPDATES_ENABLED={auto_updates_enabled}, CHECK_FREQUENCY={check_frequency}, EXTENSIONES_HABILITADAS={extensiones_habilitadas}")

def ejecutar_comando(comando):
    """Ejecuta un comando de terminal."""
    try:
        subprocess.run(comando, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error ejecutando {comando}: {e}")

def aplicar_actualizaciones(callback):
    """Ejecuta el script de actualización en Bash y captura la salida."""
    print("Iniciando script de actualización...")
    process = subprocess.Popen(f"bash {SCRIPT_PATH} --once", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    for line in iter(process.stdout.readline, ''):
        print(line.strip())
        callback(line.strip())

    process.stdout.close()
    process.wait()

def obtener_estado_extensiones():
    """Devuelve el estado de las extensiones dash-to-panel y dash-to-dock."""
    estado = {
        "dash-to-panel": False,
        "dash-to-dock": False
    }
    
    # Ejecutar el comando para obtener las extensiones habilitadas
    resultado = subprocess.run("gnome-extensions list --enabled", shell=True, text=True, capture_output=True)
    extensiones_habilitadas = resultado.stdout.splitlines()

    # Verificar el estado de cada extensión
    estado["dash-to-panel"] = "dash-to-panel@jderose9.github.com" in extensiones_habilitadas
    estado["dash-to-dock"] = "dash-to-dock@micxgx.gmail.com" in extensiones_habilitadas

    return estado

class VentanaPrincipal(Gtk.ApplicationWindow):
    """Ventana principal que unifica todo en una sola interfaz."""
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Bambú Control")
        self.set_default_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.set_resizable(False)

        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=MARGIN)
        layout.set_margin_start(MARGIN)
        layout.set_margin_end(MARGIN)
        layout.set_margin_top(MARGIN)
        layout.set_margin_bottom(MARGIN)
        self.set_child(layout)

        # Cargar logo usando LOGO_IMAGE_SIZE
        self.imagen_logo = Gtk.Image.new_from_file(os.path.join(BASE_DIR, "logo.gif"))
        self.imagen_logo.set_pixel_size(LOGO_IMAGE_SIZE)
        layout.append(self.imagen_logo)

        hbox_look = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=MARGIN)
        etiqueta_look = Gtk.Label(label="Look & Appearance")
        etiqueta_look.set_xalign(0)
        hbox_look.append(etiqueta_look)
        layout.append(hbox_look)

        # Botones para los temas Modern y Traditional
        self.boton_traditional = Gtk.Button()
        imagen_traditional = Gtk.Image.new_from_file(os.path.join(BASE_DIR, "traditional.png"))
        imagen_traditional.set_pixel_size(SMALL_IMAGE_SIZE)  # Tamaño ajustado
        self.boton_traditional.set_child(imagen_traditional)
        self.boton_traditional.connect("clicked", self.activar_traditional)

        self.boton_modern = Gtk.Button()
        imagen_modern = Gtk.Image.new_from_file(os.path.join(BASE_DIR, "modern.png"))
        imagen_modern.set_pixel_size(SMALL_IMAGE_SIZE)  # Tamaño ajustado
        self.boton_modern.set_child(imagen_modern)
        self.boton_modern.connect("clicked", self.activar_modern)

        hbox_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=MARGIN)
        hbox_buttons.append(self.boton_traditional)
        hbox_buttons.append(self.boton_modern)
        layout.append(hbox_buttons)

        # Verificar el estado de las extensiones y habilitar/deshabilitar los botones
        self.actualizar_estado_botones()

        etiqueta_actualizaciones = Gtk.Label(label="Configuración de Actualizaciones")
        etiqueta_actualizaciones.set_xalign(0)
        layout.append(etiqueta_actualizaciones)

        hbox_auto_updates = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=MARGIN)
        self.auto_updates_switch = Gtk.Switch()
        self.auto_updates_switch.set_active(read_config()["AUTO_UPDATES_ENABLED"])
        self.auto_updates_switch.connect("state-set", self.on_auto_updates_toggle)
        hbox_auto_updates.append(Gtk.Label(label="Habilitar Actualizaciones Automáticas"))
        hbox_auto_updates.append(self.auto_updates_switch)
        layout.append(hbox_auto_updates)

        frecuencia_combo = Gtk.ComboBoxText()
        frecuencia_combo.append("daily", "Diariamente")
        frecuencia_combo.append("weekly", "Semanalmente")
        frecuencia_combo.append("monthly", "Mensualmente")
        frecuencia_combo.set_active_id(read_config()["CHECK_FREQUENCY"])
        frecuencia_combo.connect("changed", self.on_frecuencia_changed)
        layout.append(Gtk.Label(label="Frecuencia de Actualizaciones"))
        layout.append(frecuencia_combo)

        # Crear el botón de actualizar y deshabilitarlo inicialmente
        self.boton_actualizar = Gtk.Button(label="Actualizar ahora")
        self.boton_actualizar.connect("clicked", self.actualizar_sistema)
        layout.append(self.boton_actualizar)

        # Cargar imagen de progreso usando PROGRESS_IMAGE_SIZE
        self.imagen_progreso = Gtk.Image.new_from_file(os.path.join(BASE_DIR, "loading.gif"))
        self.imagen_progreso.set_pixel_size(PROGRESS_IMAGE_SIZE)
        layout.append(self.imagen_progreso)
        self.imagen_progreso.hide()

        # Cargar imagen de tarea completa usando COMPLETE_IMAGE_SIZE
        self.imagen_completo = Gtk.Image.new_from_file(os.path.join(BASE_DIR, "complete.gif"))
        self.imagen_completo.set_pixel_size(COMPLETE_IMAGE_SIZE)
        layout.append(self.imagen_completo)
        self.imagen_completo.hide()

        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_vexpand(True)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        scrolled_window.set_child(self.text_view)
        layout.append(scrolled_window)

        self.text_buffer = self.text_view.get_buffer()

    def activar_traditional(self, button):
        """Activa el tema Traditional."""
        print("Activando tema Traditional...")
        ejecutar_comando("gnome-extensions disable dash-to-dock@micxgx.gmail.com")
        ejecutar_comando("gnome-extensions enable dash-to-panel@jderose9.github.com")
        self.actualizar_estado_botones()

    def activar_modern(self, button):
        """Activa el tema Modern."""
        print("Activando tema Modern...")
        ejecutar_comando("gnome-extensions disable dash-to-panel@jderose9.github.com")
        ejecutar_comando("gnome-extensions enable dash-to-dock@micxgx.gmail.com")
        self.actualizar_estado_botones()

    def on_auto_updates_toggle(self, switch, state):
        """Maneja el cambio del estado del switch de actualizaciones automáticas."""
        write_config(auto_updates_enabled=state)

    def on_frecuencia_changed(self, combo):
        """Maneja el cambio de frecuencia de actualizaciones."""
        frecuencia = combo.get_active_id()
        write_config(check_frequency=frecuencia)

    def actualizar_sistema(self, button):
        """Inicia el proceso de actualización."""
        self.text_buffer.set_text("")  # Limpia el TextView
        self.imagen_progreso.show()
        self.imagen_completo.hide()

        # Ejecuta la actualización en un hilo para no bloquear la UI
        thread = Thread(target=self.procesar_actualizacion)
        thread.start()

    def procesar_actualizacion(self):
        """Procesa la actualización y muestra el progreso."""
        aplicar_actualizaciones(self.mostrar_progreso)
        GLib.idle_add(self.mostrar_imagen_completa)

    def mostrar_progreso(self, mensaje):
        """Muestra el progreso en el TextView."""
        GLib.idle_add(self.agregar_mensaje, mensaje)

    def agregar_mensaje(self, mensaje):
        """Agrega un mensaje al TextView."""
        self.text_buffer.insert_at_cursor(mensaje + "\n")

    def mostrar_imagen_completa(self):
        """Muestra la imagen de tarea completa."""
        self.imagen_progreso.hide()
        self.imagen_completo.show()

    def actualizar_estado_botones(self):
        """Actualiza el estado de los botones en función de las extensiones activas."""
        estado = obtener_estado_extensiones()
        if estado["dash-to-panel"]:
            self.boton_modern.set_sensitive(True)  # Permitir cambiar a Modern
            self.boton_traditional.set_sensitive(False)  # No permitir cambiar a Traditional
        elif estado["dash-to-dock"]:
            self.boton_modern.set_sensitive(False)  # No permitir cambiar a Modern
            self.boton_traditional.set_sensitive(True)  # Permitir cambiar a Traditional

class Aplicacion(Gtk.Application):
    """Clase principal de la aplicación."""
    def __init__(self):
        super().__init__(application_id="org.bambucontrol.app")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        """Función que se llama al iniciar la aplicación."""
        win = VentanaPrincipal(self)
        win.present()

if __name__ == "__main__":
    app = Aplicacion()
    app.run()

