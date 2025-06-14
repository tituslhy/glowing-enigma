from neo4j import GraphDatabase
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.patches import ArrowStyle
from netgraph import Graph as ngGraph


def display_graph(uri: str, username: str, password: str):
    """
    Connects to a Neo4j database, retrieves nodes and relationships, 
    constructs a directed graph using NetworkX, and visualizes it 
    interactively using NetGraph and Matplotlib.

    Parameters:
    -----------
    uri : str
        The connection URI for the Neo4j database (e.g., "bolt://localhost:7687")
    username : str
        Username for authentication with the Neo4j database
    password : str
        Password for authentication with the Neo4j database

    Returns:
    --------
    None or str
        Displays a graph if data exists; returns a message if no data to plot.
    """

    # Step 1: Set up connection to Neo4j database
    driver = GraphDatabase.driver(uri, auth=(username, password))

    # Step 2: Cypher query to fetch all nodes and optional relationships
    query = """
    MATCH (n)
    OPTIONAL MATCH (n)-[r]->(m)
    RETURN n.name AS source_name, type(r) AS relationship_type, m.name AS target_name
    """

    def get_graph_data(tx):
        """
        Executes the Neo4j query in a read transaction and structures the data.

        Parameters:
        -----------
        tx : neo4j.Transaction
            A Neo4j transaction object

        Returns:
        --------
        tuple: (list of node names, list of edge tuples with relationship types)
        """
        result = tx.run(query)
        nodes = set()
        edges = []

        for record in result:
            source_name = record["source_name"]
            target_name = record["target_name"]
            relationship = record["relationship_type"]

            if source_name:
                nodes.add(source_name)
            if target_name:
                nodes.add(target_name)
                edges.append((source_name, target_name, relationship))

        return list(nodes), edges

    # Step 3: Run the query using a database session
    with driver.session() as session:
        nodes, edges = session.execute_read(get_graph_data)

    # Step 4: Build a directed graph using NetworkX
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    G.add_edges_from([
        (source, target, {'type': rel_type}) for source, target, rel_type in edges
    ])

    # Step 5: Set up the Matplotlib figure and axes
    fig, ax = plt.subplots(figsize=(15, 12))
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    # Step 6: Visualize the graph using NetGraph
    try:
        plot_instance = ngGraph(
            G,
            node_layout='spring',             # Layout algorithm
            node_size=5,
            node_color='lightblue',
            edge_width=0.4,
            edge_alpha=1,
            edge_color='black',
            node_labels=True,
            edge_labels=nx.get_edge_attributes(G, 'type'),
            arrows=True,
            ax=ax,
            arrowsize=1,
            edge_arrow_width=0.5,
            node_label_fontdict={'size': 12}
        )
    except:
        # If plotting fails (e.g., no nodes), clean up and exit gracefully
        plt.clf()
        plt.close(fig)
        ax.clear()
        plt.close('all')
        return "Nothing to Plot, add memories"

    plt.title("Mem0 Graph Memory Visualization", fontsize=20)

    # Step 7: Add mouse scroll zoom functionality
    def zoom_factory(ax, base_scale=2.):
        """
        Adds scroll-to-zoom functionality on the matplotlib axes.

        Parameters:
        -----------
        ax : matplotlib.axes.Axes
            The axes to apply zoom behavior
        base_scale : float
            The zoom scale factor

        Returns:
        --------
        function
            Zoom function bound to scroll events
        """
        def zoom_fun(event):
            cur_xlim = ax.get_xlim()
            cur_ylim = ax.get_ylim()
            xdata = event.xdata
            ydata = event.ydata
            if event.button == 'up':
                scale_factor = 1 / base_scale
            elif event.button == 'down':
                scale_factor = base_scale
            else:
                scale_factor = 1

            new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
            new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
            relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
            rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

            ax.set_xlim([
                xdata - new_width * (1 - relx), 
                xdata + new_width * relx
            ])
            ax.set_ylim([
                ydata - new_height * (1 - rely), 
                ydata + new_height * rely
            ])
            plt.draw()

        fig = ax.get_figure()
        fig.canvas.mpl_connect('scroll_event', zoom_fun)
        return zoom_fun

    zoom = zoom_factory(ax)

    # Step 8: Add mouse drag/pan functionality
    def on_press(event):
        """Records the starting position when mouse is pressed."""
        if event.inaxes != ax:
            return
        ax._pan_start = (event.x, event.y)

    def on_release(event):
        """Resets the pan start position when mouse button is released."""
        if event.inaxes != ax:
            return
        ax._pan_start = None

    def on_motion(event):
        """Moves the plot when mouse is dragged."""
        if event.inaxes != ax or not ax._pan_start:
            return
        dx = event.x - ax._pan_start[0]
        dy = event.y - ax._pan_start[1]

        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        scale_x = (xlim[1] - xlim[0]) / ax.get_window_extent().width
        scale_y = (ylim[1] - ylim[0]) / ax.get_window_extent().height

        ax.set_xlim(xlim - dx * scale_x)
        ax.set_ylim(ylim + dy * scale_y)

        ax._pan_start = (event.x, event.y)
        plt.draw()

    # Bind pan events to the figure
    fig.canvas.mpl_connect('button_press_event', on_press)
    fig.canvas.mpl_connect('button_release_event', on_release)
    fig.canvas.mpl_connect('motion_notify_event', on_motion)

    # Step 9: Show the final interactive graph
    plt.show()

    # Step 10: Close the Neo4j connection
    driver.close()