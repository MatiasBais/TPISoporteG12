from flask import Flask, render_template, request, Response, jsonify, redirect, url_for
import requests
from bs4 import BeautifulSoup
from lxml import etree
import json
from datetime import datetime
import database as dbase  
from product import Product
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import io
import random

db = dbase.dbConnection()

app = Flask(__name__)
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
                item_info = {
                    'Item_buscado': item,
                    'Titulo': result.get('title', ''),
                    'Precio': result.get('price', 0),
                    'URL': result.get('permalink', ''),
                    'Fecha': fecha,
                    'Img': result.get('thumbnail', '')
                }
                formatted_results.append(item_info)
             
        collection = db["melicompara"]
        collection.insert_many(formatted_results)
        return redirect(url_for("item", product_name=item, search_date=fecha))
    else:
        return render_template('index.html')
    

@app.route("/<product_name>/<search_date>")
def item(product_name, search_date):
    products = db["melicompara"]
    valores = products.find({"Item_buscado": product_name, "Fecha": search_date})
    acum = 0
    bajo2 = 9999999999999999
    alto2 = 0
    #suma de precios
    for i in valores:
        acum += int(i["Precio"])
        if(int(i["Precio"])< bajo2):
            bajo2 = int(i["Precio"])
        if(int(i["Precio"])> alto2):
            alto2 = int(i["Precio"])
    acumulado = str(int(acum/products.count_documents({"Item_buscado": product_name})))
    minItem = products.find_one({ "$and":[{"Item_buscado": product_name}, {"Precio": str(bajo2)}]})
    maxItem = products.find_one({ "$and":[{"Item_buscado": product_name}, {"Precio": str(alto2)}]})
    return render_template('index2.html', acumulado=acumulado, bajo2=bajo2, alto2=alto2, product_name=product_name.upper(), minItem=minItem, maxItem=maxItem)

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
    products = db["melicompara"]
    valores = products.find({"Item_buscado": product_name.lower()}).sort("Fecha")
    fechas=[]
    for i in valores:
        fecha = i["Fecha"]
        if fecha not in fechas:
            fechas.append(fecha)
    proms =[]
    altos=[]
    bajos=[]
    for f in fechas:
        acum = 0
        bajo2 = 99999999999999
        alto2 = 0
        count = 0
        valores = products.find({"Item_buscado": product_name.lower()})
        for i in valores:
            if (f==i["Fecha"]):
                acum += int(i["Precio"])
                count = count+1
                if(int(i["Precio"])< bajo2):
                    bajo2 = int(i["Precio"])
                if(int(i["Precio"])> alto2):
                    alto2 = int(i["Precio"])
        if (count!=0):
            proms.append(acum/count)
            altos.append(alto2)
            bajos.append(bajo2)
        else:
            fechas.remove(f)


    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    axis.plot(fechas, proms, color="green", label="Promedio",marker='o')
    axis.plot(fechas, altos, color="blue", label="Altos",marker='o')
    axis.plot(fechas, bajos, color="red", label="Bajos",marker='o')
    axis.legend()
    return fig


if __name__ == '__main__':
    app.run(debug=True, port=4000)