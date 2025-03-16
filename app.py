from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import heapq
import networkx as nx
import matplotlib.pyplot as plt
import io

app = Flask(__name__)

# Database connection
def get_db_connection():
    conn = sqlite3.connect('database/ambulance.db')
    conn.row_factory = sqlite3.Row
    return conn

# Dijkstra's Algorithm
def dijkstra(start, end):
    conn = get_db_connection()
    edges = conn.execute('SELECT start_node, end_node, distance FROM distances').fetchall()
    conn.close()

    graph = {}
    for edge in edges:
        if edge['start_node'] not in graph:
            graph[edge['start_node']] = []
        graph[edge['start_node']].append((edge['end_node'], edge['distance']))
        if edge['end_node'] not in graph:
            graph[edge['end_node']] = []
        graph[edge['end_node']].append((edge['start_node'], edge['distance']))

    pq = [(0, start)]
    distances = {start: 0}
    previous_nodes = {start: None}

    while pq:
        current_distance, current_node = heapq.heappop(pq)
        if current_node == end:
            path = []
            while previous_nodes[current_node] is not None:
                path.append(current_node)
                current_node = previous_nodes[current_node]
            path.append(start)
            path.reverse()
            return distances[end], path

        for neighbor, weight in graph.get(current_node, []):
            distance = current_distance + weight
            if neighbor not in distances or distance < distances[neighbor]:
                distances[neighbor] = distance
                previous_nodes[neighbor] = current_node
                heapq.heappush(pq, (distance, neighbor))

    return float("inf"), []

@app.route('/visualize_graph')
def visualize_graph():
    start = request.args.get('start')
    end = request.args.get('end')

    conn = get_db_connection()
    edges = conn.execute('SELECT start_node, end_node, distance FROM distances').fetchall()
    conn.close()

    # Create NetworkX Graph
    G = nx.Graph()
    for edge in edges:
        G.add_edge(edge['start_node'], edge['end_node'], weight=edge['distance'])

    # Set node positions
    pos = nx.spring_layout(G)

    plt.figure(figsize=(8, 6))

    # Draw all edges
    nx.draw(G, pos, with_labels=True, node_size=500, node_color='skyblue', edge_color='lightgray', font_size=10)

    if start and end and start in G and end in G:
        try:
            # Dijkstra shortest path
            shortest_path = nx.shortest_path(G, source=start, target=end, weight="weight")
            path_edges = list(zip(shortest_path, shortest_path[1:]))

            # Draw the shortest path in red
            nx.draw_networkx_edges(G, pos, edgelist=path_edges, edge_color='red', width=2.5)
        except nx.NetworkXNoPath:
            pass

    # Add edge weights
    labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)

    img = io.BytesIO()
    plt.savefig(img, format='PNG')
    img.seek(0)

    return send_file(img, mimetype='image/png')

@app.route('/show_graph')
def show_graph():
    path = request.args.get('path')
    start = path.split(' → ')[0]
    end = path.split(' → ')[-1]

    return render_template('graph.html', start=start, end=end)


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dijkstra')
def dijkstra_page():
    return render_template('dijkstra.html')

@app.route('/live_map')
def live_map():
    return render_template('live_map.html')

@app.route('/get_distance', methods=['POST'])
def get_distance():
    source = request.form['source']
    destination = request.form['destination']
    distance, path = dijkstra(source, destination)

    if distance == float("inf"):
        return redirect(url_for('result_page', message=f"No path found between {source} and {destination}.", path="None"))
    
    # Redirect to the result page and pass the path
    return redirect(url_for('result_page', message=f"The shortest distance between {source} and {destination} is {distance} units.", path=" → ".join(path)))

@app.route('/result')
def result_page():
    message = request.args.get('message')
    path = request.args.get('path')
    return render_template('result.html', message=message, path=path)

@app.route('/visualize_graph')
def visualize_graph_page():
    return visualize_graph()

if __name__ == '__main__':
    app.run(debug=True)
