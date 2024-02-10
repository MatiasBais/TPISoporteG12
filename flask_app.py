from flask import Flask, request, redirect, url_for, render_template, Response
import requests
import mysql.connector
from datetime import datetime
from database import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io
import matplotlib.dates as mdates

app = Flask(__name__)

# Establish a connection to your MySQL database
db_connection = mysql.connector.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DATABASE
)

#Method get
@app.route('/', methods=['POST', 'GET'])
def get_item():
    if request.method == 'POST':
        item = request.form["it"].lower()
        API_ENDPOINT = 'https://api.mercadolibre.com/sites/MLA/search'
        API_KEY = 'Sk9ad1lvdqhUsVc4VWdSX1L1f648zxsJ'
        fecha = str(datetime.now())
        fecha = fecha[:10]

        # Make the request to the MercadoLibre API
        params = {'q': item, 'limit': 10}  # You can adjust the limit as needed
        headers = {'Authorization': f'Bearer {API_KEY}'}
        response = requests.get(API_ENDPOINT, params=params, headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            results = data.get('results', [])

            # Extract relevant information from the response
            formatted_results = []
            for result in results:
                item_info = (
                    item,
                    result.get('title', ''),
                    result.get('price', 0),
                    result.get('permalink', ''),
                    fecha,
                    result.get('thumbnail', '')
                )
                formatted_results.append(item_info)

            # Insert the data into MySQL
            cursor = db_connection.cursor()
            sql = "INSERT INTO melicompara (Item_buscado, Titulo, Precio, URL, Fecha, Img) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.executemany(sql, formatted_results)
            db_connection.commit()
            cursor.close()

            return redirect(url_for("item", product_name=item, search_date=fecha))
    else:
        return render_template('index.html')

@app.route("/<product_name>/<search_date>")
def item(product_name, search_date):
    cursor = db_connection.cursor(dictionary=True)
    sql = "SELECT * FROM melicompara WHERE Item_buscado = %s AND Fecha = %s"
    cursor.execute(sql, (product_name, search_date))
    results = cursor.fetchall()
    cursor.close()

    acum = sum(int(result["Precio"]) for result in results)
    promedio = acum / len(results)

    minItem = min(results, key=lambda x: int(x["Precio"]))
    maxItem = max(results, key=lambda x: int(x["Precio"]))

    return render_template('index2.html',
                           acumulado=promedio,
                           bajo2=minItem["Precio"],
                           alto2=maxItem["Precio"],
                           product_name=product_name.upper(),
                           minItem=minItem,
                           maxItem=maxItem
                          )

@app.errorhandler(404)
def notFound(error=None):
    message ={
        'message': 'No encontrado ' + request.url,
        'status': '404 Not Found'
    }
    response = jsonify(message)
    response.status_code = 404
    return response

@app.route('/plot.png/<product_name>')
def plot_png(product_name):
    fig = createGraph(product_name.lower())
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')

def createGraph(product_name):
    cursor = db_connection.cursor(dictionary=True)
    sql = "SELECT Fecha, AVG(Precio) as Promedio, MAX(Precio) as Maximo, MIN(Precio) as Minimo FROM melicompara WHERE Item_buscado = %s GROUP BY Fecha"
    cursor.execute(sql, (product_name,))
    results = cursor.fetchall()
    cursor.close()

    fechas = [result["Fecha"] for result in results]
    promedios = [result["Promedio"] for result in results]
    maximos = [result["Maximo"] for result in results]
    minimos = [result["Minimo"] for result in results]

    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    axis.plot(fechas, promedios, color="green", label="Promedio", marker='o')
    axis.plot(fechas, maximos, color="blue", label="Altos", marker='o')
    axis.plot(fechas, minimos, color="red", label="Bajos", marker='o')
    axis.legend()
    axis.tick_params(axis='x', rotation=90)
    axis.tick_params(axis='both', which='major', labelsize=6)
    axis.xaxis.set_major_formatter(mdates.DateFormatter('%y-%m-%d'))
    return fig

if __name__ == '__main__':
    app.run(debug=True, port=4000)
