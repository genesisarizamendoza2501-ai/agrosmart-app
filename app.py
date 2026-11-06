from flask import Flask, render_template, request, jsonify, send_file
import requests
import io
import sqlite3
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = Flask(__name__)

AZURE_ENDPOINT = "Escribe tu URL de Azure OpenAI aquí"  # Reemplaza con tu endpoint de Azure OpenAI
AZURE_API_KEY = "YOUR_AZURE_API_KEY_HERE"  # Reemplaza con tu clave de API de Azure

# Inicializar Base de Datos SQLite 
def init_db():
    conn = sqlite3.connect('agrosmart.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bitacora (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            cultivo TEXT,
            etapa TEXT,
            superficie TEXT,
            ubicacion TEXT,
            consulta TEXT,
            respuesta TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/weather', methods=['POST'])
def get_weather():
    # Simulación de clima inteligente basado en la región o datos meteorológicos
    data = request.json
    ubicacion = data.get('ubicacion', 'Centro México')
    # Datos simulados profesionales para el panel
    return jsonify({
        "temp": "24°C",
        "humedad": "68%",
        "lluvia": "10% (Bajo riesgo)",
        "evapotranspiracion": "4.2 mm/día",
        "recomendacion_riego": "Favorable para riego matutino."
    })

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        cultivo = data.get('cultivo', 'No especificado')
        etapa = data.get('etapa', 'No especificada')
        tamano = data.get('tamano', 'No especificado')
        ubicacion = data.get('ubicacion', 'No especificada')
        image_data = data.get('image', None)

        system_instruction = (
            "Eres AgroSmart, un asistente agrónomo experto de nivel corporativo que apoya a productores agrícolas. "
            "Responde de manera clara, estructurada y profesional. "
            f"DATOS DE LA PARCELA ACTIVA: Cultivo: {cultivo} | Etapa: {etapa} | Superficie: {tamano} | Ubicación: {ubicacion}."
        )

        messages = [{"role": "system", "content": system_instruction}]

        if image_data:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_message if user_message else "Analiza esta imagen fitosanitaria de mi cultivo."},
                    {"type": "image_url", "image_url": {"url": image_data}}
                ]
            })
        else:
            messages.append({"role": "user", "content": user_message})

        payload = {"messages": messages}
        headers = {"Content-Type": "application/json", "api-key": AZURE_API_KEY}

        response = requests.post(AZURE_ENDPOINT, json=payload, headers=headers, timeout=45)
        
        if response.status_code == 200:
            result = response.json()
            bot_reply = result['choices'][0]['message']['content']
            
            # Guardar en base de datos SQLite
            conn = sqlite3.connect('agrosmart.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO bitacora (fecha, cultivo, etapa, superficie, ubicacion, consulta, respuesta)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (datetime.now().strftime("%Y-%m-%d %H:%M"), cultivo, etapa, tamano, ubicacion, user_message, bot_reply))
            conn.commit()
            conn.close()

            return jsonify({"response": bot_reply})
        else:
            return jsonify({"response": f"Error en Azure ({response.status_code}): {response.text}"}), response.status_code

    except Exception as e:
        return jsonify({"response": f"Error interno en el servidor: {str(e)}"}), 500

@app.route('/history', methods=['GET'])
def get_history():
    conn = sqlite3.connect('agrosmart.db')
    cursor = conn.cursor()
    cursor.execute('SELECT fecha, cultivo, consulta, respuesta FROM bitacora ORDER BY id DESC LIMIT 10')
    rows = cursor.fetchall()
    conn.close()
    
    history = [{"fecha": r[0], "cultivo": r[1], "consulta": r[2], "respuesta": r[3]} for r in rows]
    return jsonify(history)

@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    try:
        data = request.json
        cultivo = data.get('cultivo', 'Jitomate')
        etapa = data.get('etapa', 'Floración')
        tamano = data.get('tamano', '2 Hectáreas')
        ubicacion = data.get('ubicacion', 'Centro México')
        recommendation = data.get('recommendation', 'Sin recomendaciones registradas.')

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#0b2a1a'), spaceAfter=6)
        subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#10b981'), spaceAfter=15)
        section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#0b2a1a'), spaceBefore=10, spaceAfter=6)
        body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#222222'), spaceAfter=8, leading=14)

        story.append(Paragraph("AgroSmart Enterprise", title_style))
        story.append(Paragraph("Reporte Técnico Integral y Bitácora de Parcela", subtitle_style))
        
        data_table = [
            [Paragraph("<b>Cultivo:</b>", body_style), Paragraph(cultivo, body_style), Paragraph("<b>Superficie:</b>", body_style), Paragraph(tamano, body_style)],
            [Paragraph("<b>Etapa Fenológica:</b>", body_style), Paragraph(etapa, body_style), Paragraph("<b>Región / Clima:</b>", body_style), Paragraph(ubicacion, body_style)]
        ]
        t = Table(data_table, colWidths=[110, 150, 100, 180])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ecfdf5')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#10b981')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#0b2a1a')),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))

        story.append(Paragraph("Dictamen Técnico Reciente (Azure AI Foundry):", section_style))
        story.append(Paragraph(recommendation.replace('\n', '<br/>'), body_style))
        
        story.append(Spacer(1, 20))
        story.append(Paragraph("<i>Reporte oficial generado por AgroSmart Enterprise - Módulo Multi-Predio y Base de Datos Corporativa.</i>", ParagraphStyle('Footer', parent=styles['Italic'], fontSize=8, textColor=colors.HexColor('#666666'))))

        doc.build(story)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="Reporte_Corporativo_AgroSmart.pdf", mimetype='application/pdf')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)