#!/bin/bash

# Archivo de configuración
CONFIG_FILE="/var/home/$USER/.local/share/applications/bambu-control/update_config.conf"

# Función para leer el archivo de configuración
read_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        source "$CONFIG_FILE"
    else
        echo "El archivo de configuración no existe, usando valores por defecto."
        AUTO_UPDATES_ENABLED="true"
        CHECK_FREQUENCY="daily"  # Valor por defecto
        LAST_UPDATE_CHECK=0
        STORED_VERSION=""
    fi
}

# Función para guardar configuraciones en el archivo
save_config() {
    cat <<EOL > "$CONFIG_FILE"
AUTO_UPDATES_ENABLED=$AUTO_UPDATES_ENABLED
CHECK_FREQUENCY=$CHECK_FREQUENCY
LAST_UPDATE_CHECK=$LAST_UPDATE_CHECK
STORED_VERSION=$STORED_VERSION
EOL
}

# Función para enviar notificaciones
send_notification() {
    TITLE="$1"
    MESSAGE="$2"
    notify-send "$TITLE" "$MESSAGE"
    echo "$TITLE: $MESSAGE"
}

# Función para verificar si ha pasado el tiempo necesario desde la última verificación
check_time_interval() {
    case "$CHECK_FREQUENCY" in
        "hourly")
            REQUIRED_INTERVAL=$((60*60))   # 1 hora en segundos
            ;;
        "daily")
            REQUIRED_INTERVAL=$((24*60*60))  # 1 día en segundos
            ;;
        "weekly")
            REQUIRED_INTERVAL=$((7*24*60*60))  # 1 semana en segundos
            ;;
        *)
            REQUIRED_INTERVAL=$((24*60*60))  # Por defecto, 1 día en segundos
            ;;
    esac

    CURRENT_TIME=$(date +%s)
    TIME_DIFF=$((CURRENT_TIME - LAST_UPDATE_CHECK))

    if [[ $TIME_DIFF -lt $REQUIRED_INTERVAL ]]; then
        echo "Todavía no ha pasado el intervalo necesario para la siguiente verificación."
        return 1  # No ha pasado el tiempo suficiente
    fi

    return 0  # Ha pasado suficiente tiempo
}

# Función para verificar nuevas versiones de Fedora Silverblue (rebase)
check_silverblue_version() {
    echo "Verificando la última versión de Fedora Silverblue..."

    LATEST_VERSION=$(cat "/var/home/$USER/.local/share/applications/bambu-control/latest-release")

    # Verificar si hubo algún error al obtener la versión
    if [[ -z "$LATEST_VERSION" ]]; then
        send_notification "Error" "No se pudo verificar la última versión de Silverblue."
        return
    fi

    # Comparar versiones
    if [[ "$LATEST_VERSION" != "$STORED_VERSION" ]]; then
        STORED_VERSION="$LATEST_VERSION"
        save_config  # Guardar la nueva versión en el archivo de configuración
        send_notification "Nueva versión de Fedora Silverblue" "Nueva versión disponible: $LATEST_VERSION. Aplicando rebase..."

        # Aplicar nueva versión (rebase)
        echo "Aplicando rebase a la versión: $LATEST_VERSION..."
        rpm-ostree rebase "${LATEST_VERSION}"

        if [[ $? -eq 0 ]]; then
            send_notification "Actualización completada" "Fedora Silverblue actualizado a la versión $LATEST_VERSION."
        else
            send_notification "Error" "Ocurrió un error al aplicar el rebase a la versión $LATEST_VERSION."
        fi
    else
        echo "No hay nuevas versiones de Silverblue disponibles."
    fi
}

# Función para aplicar actualizaciones del sistema (paquetes)
apply_updates() {
    echo "Aplicando actualizaciones del sistema..."

    rpm-ostree upgrade

    # Verificar si no hay actualizaciones
    if rpm-ostree upgrade | grep -q "No upgrade available"; then
        send_notification "Sin actualizaciones" "No hay actualizaciones de paquetes disponibles."
    else
        if [[ $? -eq 0 ]]; then
            send_notification "Actualización aplicada" "Se aplicaron todas las actualizaciones correctamente."
        else
            send_notification "Error" "Ocurrió un error al aplicar las actualizaciones."
        fi
    fi
}

# Función principal para la ejecución continua
continuous_execution() {
    while true; do
        read_config

        if [[ "$AUTO_UPDATES_ENABLED" == "true" ]]; then
            if check_time_interval; then
                apply_updates
                check_silverblue_version
                LAST_UPDATE_CHECK=$(date +%s)  # Actualizar la hora de la última verificación
                save_config  # Guardar la hora actual en el archivo de configuración
            else
                echo "No se ha alcanzado el tiempo mínimo para la siguiente verificación."
                # Espera hasta que haya pasado el intervalo requerido
                sleep $((REQUIRED_INTERVAL - TIME_DIFF))
            fi
        else
            echo "Actualizaciones automáticas deshabilitadas."
            sleep 3600  # Esperar una hora antes de verificar nuevamente
        fi
    done
}

# Función para la ejecución manual única
single_execution() {
    read_config

    # Ejecutar las actualizaciones siempre, sin verificar AUTO_UPDATES_ENABLED
    apply_updates
    check_silverblue_version
    LAST_UPDATE_CHECK=$(date +%s)  # Actualizar la hora de la última verificación
    save_config  # Guardar la hora actual en el archivo de configuración
}

# Detectar si el script ha sido invocado con un argumento
if [[ "$1" == "--once" ]]; then
    single_execution
else
    continuous_execution
fi
