from pathlib import Path
from itertools import zip_longest
from tkinter import filedialog, messagebox
from pycaw.pycaw import AudioUtilities
from playwright.sync_api import sync_playwright
import re
import os
import tkinter as tk
import pygetwindow as gw
import psutil
import threading
from tkinter import ttk



# Función para mostrar mensajes en la barra de estado de la ventana
def actualizar_mensaje(mensaje):
    barra_estado.config(text=mensaje)
    ventana.after(100, ventana.update_idletasks())

barra_estado=(True)


# Función para mostrar un mensaje de carga
def mostrar_carga(mensaje):
    barra_estado.config(text=mensaje)
    ventana.update_idletasks()

# Función para buscar ventanas con guion medio y excluir otras ventanas
def buscar_ventanas_con_guion():
    windows = gw.getWindowsWithTitle("")
    return next(
        (win.title for win in windows if '-' in win.title and 
        not any(excluido in win.title for excluido in ['Visual Studio Code', 'Chrome', 'Spotify Premium','Steam (32 bits)',
                                                        'Microsoft', 'Explorador', 'Discord', 'Telegram',
                                                        'WhatsApp', 'Slack', 'Zoom', 'Stremio', 'Mozilla Firefox',
                                                        'Brave', 'Opera', 'Microsoft Edge', 'Microsoft', 'WhatsApp',
                                                        'Stremio', 'Brave', 'Opera', 'Bloc', 'MiniLyrics',
                                                        'MiniLyrics - Display lyrics automatically',
                                                        'Steam','Friends', 'Steam Overlay', 'Steam -', 'Steam Community',
                                                        'Steam Web Helper', 'Big Picture Mode' 
                                                        ])),
        None
    )

# Función para iniciar la animación de carga
def iniciar_carga():
    barra_progreso.start()
    mostrar_carga("Procesando...")

# Función para detener la animación de carga
def detener_carga():
    barra_progreso.stop()
    mostrar_carga("Listo")


#-------------------------------limpiar nombre de cancion---------------------
def limpiar_nombre(nombre):
    # Reemplazar ":" y otros caracteres no deseados por 0 espacio 
    caracteres_no_permitidos = r'[\/:*?"<>|]'  # Caracteres no permitidos en nombres de archivo
    nombre_limpio = re.sub(caracteres_no_permitidos, "", nombre)  # Reemplazar por 0 espacio
    return nombre_limpio.strip()  # Eliminar espacios adicionales al inicio o final


# Función para buscar letras localmente y si no las encuentra las busca en la web y las traduce
def buscar_letras():
    toggle_barra_progreso(mostrar=True)  # Mostrar la barra de progreso
    try:
        SONG = obtener_nombre_cancion()
        if not SONG:
            return

        # Limpiar el nombre de la canción
        SONG = limpiar_nombre(SONG)
        #max_lenght = 35
        actualizar_nombre_cancion(SONG)
        mostrar_carga(f"Buscando letra para: {SONG}...")

        documentos_path = str(Path.home() / "Documents")
        folder_path = os.path.join(documentos_path, "xlyrics")
        archivo_letra = os.path.join(folder_path, f"{SONG}.lrc")

        if os.path.exists(archivo_letra):
            mostrar_carga(f"Letra encontrada en la carpeta: {archivo_letra}")
            leer_archivo_lrc(SONG)
            detener_carga()
            return

        mostrar_carga(f"Letra no encontrada, buscando en la Web para: {SONG}...")
        letra_original, letra_traducida = buscar_y_traducir_letra_web(SONG)

        if letra_original and letra_traducida:
            guardar_letra_y_traduccion(SONG, letra_original, letra_traducida)
            mostrar_en_ventana(letra_original, letra_traducida)
            mostrar_carga("Proceso completado.")
        else:
            mostrar_carga("No se pudo encontrar ni traducir la letra.")

    except Exception as e:
        detener_carga()
        messagebox.showerror("Error", f"Ocurrió un error en buscar_letras: {e}")
    finally:
        ventana.after(2000, lambda: finalizar_busqueda())


# Función para obtener el nombre de la canción
def obtener_nombre_cancion():
    toggle_barra_progreso(mostrar=True)  # Mostrar la barra de progreso
    mostrar_carga("Buscando ventanas con guion...")
    SONG = buscar_ventanas_con_guion()
    if not SONG:
        messagebox.showerror("Error", "No se encontró ninguna reproducción.")
    return SONG


# Función Usa Playwright para automatizar la búsqueda de letras en AZLyrics y su traducción en Google Translate.
def buscar_y_traducir_letra_web(song_name):
    try:
        iniciar_carga()
        toggle_barra_progreso(mostrar=True)  # Mostrar la barra de progreso
        with sync_playwright() as p:
            chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
            browser = p.chromium.launch(executable_path=chrome_path)
            page = browser.new_page()

            mostrar_carga(f"Navegando en búsqueda de {song_name}...")
            lyrics = buscar_letra_azlyrics(page, song_name)
            if not lyrics:
                mostrar_carga("No se encontró la letra en AZLyrics.")
                browser.close()
                return None, None

            mostrar_carga("Traduciendo la letra...")
            translated_lines = traducir_letra_google_translate(browser, lyrics)
        
            browser.close()
            return lyrics.splitlines(), translated_lines
    except TimeoutError:
        mostrar_carga("La página tardó demasiado en cargar. Intentando de nuevo...")
        return None, None



"""    Busca la letra de una canción en AZLyrics.
    Args:        page: Instancia de la página de Playwright.
        song_name (str): Nombre de la canción a buscar.
    Returns:   str: Letra de la canción si se encuentra, None si no se encuentra.
"""
def buscar_letra_azlyrics(page, song_name):
    toggle_barra_progreso(mostrar=True)  # Mostrar la barra de progreso
    page.goto("https://search.azlyrics.com/")
    page.fill("input[type='text']", song_name)
    page.click("button:has-text('Search')")
    page.wait_for_selector("tbody tr", timeout=60000)
    page.locator("tbody tr").nth(0).click()
    lyrics = page.locator('div.col-xs-12.col-lg-8.text-center > div:not([class])').first.inner_text()
    return re.sub(r'[.!;]', '', lyrics)


# Función para traducir la letra usando Google Translate
def traducir_letra_google_translate(browser, lyrics):
    toggle_barra_progreso(mostrar=True)  # Mostrar la barra de progreso
    translate_page = browser.new_page()
    translate_page.goto("https://translate.google.com/?hl=es&sl=auto&tl=es&text=%0A&op=translate")
    translate_page.fill("textarea.er8xn", lyrics)
    translate_page.wait_for_timeout(8000)
    return translate_page.locator("span[jsname='W297wb']").all_inner_texts()
    

""" 
def traducir_letra_deepl(browser, lyrics):
    toggle_barra_progreso(mostrar=True)  # Mostrar la barra de progreso
    translate_page = browser.new_page()
    translate_page.goto("https://www.deepl.com/en/translator#en/es/es")
    
    # Esperar a que el área de texto esté disponible
    #translate_page.wait_for_selector("textarea[dl-test='translator-source-input']")
    translate_page.wait_for_selector("//*[@id="textareasContainer"]/div[3]/section/div[1]/d-textarea")
    translate_page.fill("textarea[dl-test='translator-source-input']", lyrics)
    
    # Esperar a que la traducción se complete
    translate_page.wait_for_timeout(8000)  # Ajusta este tiempo según sea necesario
    
    # Obtener la traducción
    translated_text = translate_page.locator("div[dl-test='translator-target-input']").inner_text()
    return translated_text.splitlines()
 """

# Función para procesar letras originales y traducidas
def procesar_letras(original_lyrics, translated_lines):
    original_lines = [line.strip() for line in original_lyrics.splitlines() if line.strip()]
    translated_lines = [line.strip() for line in translated_lines if line.strip()]
    return list(zip_longest(original_lines, translated_lines, fillvalue=""))


# Función para guardar letra y traducción en un archivo lrc
def guardar_letra_y_traduccion(song, letra_original, letra_traducida):
    try:
        letras_procesadas = procesar_letras("\n".join(letra_original), letra_traducida)
        documentos_path = str(Path.home() / "Documents")
        folder_path = os.path.join(documentos_path, "xlyrics")

        if not os.path.exists(folder_path):
            mostrar_carga(f"Creando carpeta: {folder_path}...")
            os.makedirs(folder_path)

        archivo_letra = os.path.join(folder_path, f"{song}.lrc")
        with open(archivo_letra, 'w', encoding='utf-8') as f:
            for original, translated in letras_procesadas:
                f.write(f"{original.strip()}\n{translated.strip()}\n")
        mostrar_carga(f"Letra y traducción guardadas en: {archivo_letra}")
    except Exception as e:
        mostrar_carga(f"Error al guardar la letra: {e}")


# Función para imprimir la letra y la traducción en la ventana desde el lrc
def mostrar_en_ventana(letra_original, letra_traducida):
    resultado.delete(1.0, tk.END)  # Borrar el contenido anterior
    letras_procesadas = procesar_letras("\n".join(letra_original), letra_traducida)

    for i, (original, translated) in enumerate(letras_procesadas):
        # Insertar letra original en verde
        resultado.insert(tk.END, f"{original}\n", "original")
        # Insertar traducción en blanco
        resultado.insert(tk.END, f"{translated}\n", "traduccion")
        resultado.insert(tk.END, "\n")  # Agregar una línea en blanco
    actualizar_mensaje("traducción mostradas en la ventana .")


# Función para actualizar el nombre de la canción en la ventana
def actualizar_nombre_cancion(nombre):
    max_length= 35  # Máximo número de caracteres para el nombre de la cancion
    nombre_formateado = (nombre[:max_length] + "...") if len(nombre) > max_length else nombre
    nombre_cancion_label.config(text=nombre_formateado)
    #nombre_cancion_label.config(justify="center")
    nombre_cancion_label.config(text=nombre, fg="#ffffff")
    #
    ventana.update()
    ventana.after(2000, lambda: nombre_cancion_label.config(fg="#ffcc00"))

SONG = buscar_ventanas_con_guion()
documentos_path = str(Path.home() / "Documents")

# Crear la ruta completa para tu carpeta de letras
folder_path = os.path.join(documentos_path, "xlyrics")
archivo_letra = os.path.join(folder_path, f"{SONG}.lrc")


# Función para abrir archivos
def abrir_archivo():
    global SONG
    SONG = buscar_ventanas_con_guion()
    if not SONG:
        messagebox.showerror("Error", "No se encontró ninguna reproducción.")
        return
    ruta_completa = os.path.join(folder_path, f"{SONG}.lrc")
    if os.path.exists(ruta_completa):
        if not hasattr(ventana, 'texto'):
            crear_area_texto()
        with open(ruta_completa, 'r', encoding='utf-8') as f:
            contenido = f.read()
        ventana.texto.delete(1.0, tk.END)
        ventana.texto.insert(tk.END, contenido)
        aplicar_colores()
        centrar_texto()
        ventana.update_idletasks()
        # Simular un proceso largo (por ejemplo, 3 segundos)
        ventana.after(2000, lambda: finalizar_busqueda())    
    else:
        messagebox.showerror("Error", f"No se encontró el archivo: {SONG}.lrc")


# Función para leer archivos LRC
def leer_archivo_lrc(SONG):
    ruta_completa = os.path.join(folder_path, f"{SONG}.lrc")
    if os.path.exists(ruta_completa):
        try:
            with open(ruta_completa, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            letra_original = []
            letra_traducida = []
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                if i % 2 == 0:
                    letra_original.append(line)
                else:
                    letra_traducida.append(line)
            mostrar_en_ventana(letra_original, letra_traducida)
            mostrar_carga(f"Letra encontrada y mostrada en la ventana.")
            # Simular un proceso largo (por ejemplo, 2 segundos)
            ventana.after(2000, lambda: finalizar_busqueda())  
        except Exception as e:
            mostrar_carga(f"Error al leer el archivo LRC: {e}")
    else:
        mostrar_carga(f"No se encontró el archivo LRC para {SONG}.")


# Función para centrar el texto en el área de texto
def centrar_texto():
    ventana.texto.tag_configure("center", justify='center')  # Configurar la etiqueta "center"
    ventana.texto.tag_add("center", 1.0, tk.END)  # Aplicar la etiqueta a todo el texto


# Función para aplicar colores al texto
def aplicar_colores():
    contenido = ventana.texto.get("1.0", tk.END).split("\n")
    for i, linea in enumerate(contenido):
        if linea.strip():
            inicio = f"{i + 1}.0"
            fin = f"{i + 1}.{len(linea)}"
            if i % 2 == 0:
                ventana.texto.tag_configure("cyan", foreground="cyan")
                ventana.texto.tag_add("cyan", inicio, fin)
            elif i % 2 == 1:
                ventana.texto.tag_configure("rosa", foreground="pink")
                ventana.texto.tag_add("rosa", inicio, fin)


# Función para crear el área de texto
def crear_area_texto():
    ventana.texto = tk.Text(ventana, wrap=tk.WORD, fg="white", font=("Helvetica", 10))
    ventana.texto.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
    ventana.texto.configure(bg="#1e1e1e")


# Función para guardar archivos
def guardar_archivo():
    if hasattr(ventana, 'texto'):
        ruta_completa = os.path.join(folder_path, f"{SONG}.lrc")
        with open(ruta_completa, 'w', encoding='utf-8') as f:
            f.write(ventana.texto.get(1.0, tk.END))
        messagebox.showinfo("Guardado", "Archivo guardado correctamente.")
        ventana.texto.destroy()
        delattr(ventana, 'texto')
        buscar_letras()
    else:
        messagebox.showwarning("Advertencia", "No hay ningún archivo abierto.")

#---------------------------------------------------------------------------------------

# Configuración de la ventana
ventana = tk.Tk()
ventana.title("🎶Lyrics & Traductor by xTian v1.1🎶")
ventana.geometry("400x800")
ventana.configure(bg="#1e1e1e")
ventana.attributes('-alpha', 0.9)


# Función para mostrar u ocultar la barra de progreso
def toggle_barra_progreso(mostrar=True):
    if mostrar:
        barra_progreso.pack(side=tk.BOTTOM, pady=5)  # Mostrar la barra de progreso
    else:
        barra_progreso.pack_forget()  # Ocultar la barra de progreso


def finalizar_busqueda():
    barra_progreso.stop()  # Detener la animación de la barra de progreso
    toggle_barra_progreso(mostrar=False)  # Ocultar la barra de progreso
    actualizar_mensaje("Proceso completado.")  # Actualizar el mensaje en la barra de estado

# Función para actualizar el mensaje en la barra de estado
def actualizar_mensaje(mensaje):
    barra_estado.config(text=mensaje)


# Simular un proceso largo (por ejemplo, 2 segundos)
ventana.after(2000, lambda: finalizar_busqueda())    

# Botón para buscar letras
boton_buscar = tk.Button(
    ventana, 
    text="Buscar", 
    command=lambda: threading.Thread(target=buscar_letras).start(), 
    bg="#333333", 
    fg="#ffffff", 
    font=("Helvetica", 12, "bold"), 
    relief=tk.RAISED, 
    activebackground="#555555", 
    activeforeground="#ffcc00", 
    cursor="hand2"
)
boton_buscar.pack(pady=15)

# Frame para botones de abajo
frame_botones = tk.Frame(ventana, bg="#1e1e1e")
frame_botones.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

# Botón para abrir archivos
boton_abrir = tk.Button(
    frame_botones,
    text="Abrir Archivo",
    command=abrir_archivo,
    bg="#333333", 
    fg="#ffffff", 
    cursor="hand2",
)
boton_abrir.pack(side=tk.LEFT, padx=5, pady=5)

# Botón para guardar archivos
boton_guardar = tk.Button(
    frame_botones,
    text="Guardar Archivo",
    command=guardar_archivo,
    bg="#333333", 
    fg="#ffffff", 
    cursor="hand2",
)
boton_guardar.pack(side=tk.RIGHT, padx=5, pady=5)

# Etiqueta para mostrar el nombre de la canción
nombre_cancion_label = tk.Label(ventana, text="", bg="#1e1e1e", fg="#ffcc00", font=("Helvetica", 14, "bold"))
nombre_cancion_label.pack(pady=0)

# Área de texto para mostrar resultados
resultado = tk.Text(ventana, wrap=tk.WORD, bg="#1e1e1e", fg="#ffffff", font=("Courier New", 12), insertbackground="white")
resultado.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Configuración de etiquetas para colores
resultado.tag_configure("original", foreground="#32cd32", font=("Helvetica", 12, "bold"), justify="center")
resultado.tag_configure("traduccion", foreground="#ffffff", font=("Helvetica", 11, "italic"), justify="center")

# Configurar el estilo para la barra de progreso
style = ttk.Style()
style.configure(
    "TProgressbar",
    thickness=10,  # Grosor de la barra
    background="black",  # Color de la barra de progreso
    troughcolor="black"  # Color de fondo de la barra
)

# Barra de progreso
barra_progreso = ttk.Progressbar(
    frame_botones, 
    orient="horizontal", 
    length=150, 
    mode="determinate",
    style="TProgressbar",
)

#barra_progreso.pack(pady=10)
barra_progreso.pack(side=tk.BOTTOM, padx=5, pady=5)

# Barra de estado
barra_estado = tk.Label(ventana, text="Esperando acción...", bg="#1e1e1e", fg="#ffffff", font=("Helvetica", 10))
barra_estado.pack(side=tk.BOTTOM, fill=tk.X)


# Simular un proceso largo (por ejemplo, 3 segundos)
ventana.after(2000, lambda: finalizar_busqueda())    

# Iniciar la ventana
ventana.mainloop()
