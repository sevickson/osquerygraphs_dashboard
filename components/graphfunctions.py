import graphistry, pandas as pd, streamlit as st
from components import secrets_beta

@st.cache(suppress_st_warning=True, allow_output_mutation=True, hash_funcs={pd.DataFrame: lambda _: None})
def fetch_csv(url):
    df_r = pd.read_csv(url)
    return(df_r)

#Use below function to split a comma-separated field into separate rows to make individual connections.
def split_intersect(df,split_column):
    df_split = df[split_column].str.split(',').apply(pd.Series, 1).stack()
    df_split.index = df_split.index.droplevel(-1)
    df_split.name = 'output'
    df_split = df_split.str.strip()

    df_join = df.join(df_split)
    # Remove rows where Table.Columnm and output are the same, this is self-reference
    df_join = df_join[df_join['Table.Column'] != df_join['output']]
    return(df_join)

#Function to transform the nodes into edges.
def node_to_edge(g,type_column,replace_name):
    # After creation of g use below to remove nodes and change the nodes to edges
    find_name = type_column
    #Remove the nodes that have a specific type and only keep the other nodes and feed it back into the df.
    good_nodes=g._nodes[g._nodes['type'] != type_column]
    good_edges=g._edges.replace(find_name,replace_name,regex=True)
    gr = g.nodes(good_nodes).edges(good_edges)
    return(gr)

def node_decorator(nodes,lvl1,lvl2,edges):
    #subsitute nodeTitle from Table.Column to Column
    nodes['node_title'] = [n_title.split(".")[1] if n_type == lvl2 else n_title for (n_type,n_title) in zip(nodes['type'],nodes['nodeTitle'])]

    # Calculate the degrees based on the `edges` to be used in the radius assignment
    src_count = edges['src'].value_counts()
    dst_count = edges['dst'].value_counts()
    src_dst_count = pd.concat([src_count, dst_count], axis=1).fillna(0).reset_index()
    src_dst_count['src_dst_count'] = src_dst_count['src'] + src_dst_count['dst']
    src_dst_count.rename(columns={'index':'nodeID'}, inplace=True)
    nodes = pd.merge(nodes,src_dst_count,on=['nodeID'])

    # Setting radius to create circle like features
    nodes['radius'] = [2000 if node_type == lvl1 else 1000 for node_type in nodes['type']]
    return(nodes)

# Add extra data to nodes
def node_add_data(df,nodes):
    groups_table = {}
    # Copy Table to colall if Table
    groups_ints_t = nodes.groupby('Table')['Table'].unique().apply(''.join).to_dict()
    for k, grt in groups_ints_t.items():
        groups_table[k] = grt
    
    # Concat intersect to Table.Column nodes as extra info making filtering easier
    groups_tcol = {}
    groups_ints_tcol = df.groupby('Table.Column')['intersect'].unique().apply(', '.join).to_dict()
    for k, grtcol in groups_ints_tcol.items():
        grtcol_split_set = set(grtcol.split(', '))
        grtcol_join = ', '.join(grtcol_split_set)
        groups_tcol[k] = grtcol_join

    # Merge the dictionaries
    groups_table.update(groups_tcol)

    nodes['z_tableFilter'] = nodes['nodeTitle'].map(groups_table)
    return(nodes)

# Remove edges and add data for filtering
def edge_rem_data(edges):
    # Remove edges where Table name is the same, meaning edges to the same table
    edges[['src_base']] = [src.rsplit('.',1)[0] if edge == 'Table.Column::Table.Column' else 'src' for (edge,src) in zip(edges['edgeType'],edges['src'])]
    edges[['dst_base']] = [dst.rsplit('.',1)[0] if edge == 'Table.Column::Table.Column' else 'dst' for (edge,dst) in zip(edges['edgeType'],edges['dst'])]
    edges = edges[edges['src_base'] != edges['dst_base']]
    edges.drop(columns=['src_base', 'dst_base'], inplace=True)

    # To avoid SettingWithCopyWarning
    edges_1 = edges.copy()
    # Create filtering table to be able to filter edges and nodes to each other for path to and from tables
    edges_1['z_tableFilter'] = edges_1['src'] + ', ' + edges_1['dst']

    # Create column to be able to filter on edges between different column names, to get a view of possible inconsistent naming
    edges_1[['src_leaf']] = [src.rsplit('.',1)[1] if edge == 'Table.Column::Table.Column' else 'src' for (edge,src) in zip(edges_1['edgeType'],edges_1['src'])]
    edges_1[['dst_leaf']] = [dst.rsplit('.',1)[1] if edge == 'Table.Column::Table.Column' else 'dst' for (edge,dst) in zip(edges_1['edgeType'],edges_1['dst'])]

    edges_1['colSim'] = ['True' if (sl==dl) else 'False' if et == 'Table.Column::Table.Column' else 'Table' for sl,dl,et in zip(edges_1['src_leaf'],edges_1['dst_leaf'],edges_1['edgeType'])]
    edges_1.drop(columns=['src_leaf', 'dst_leaf'], inplace=True)
    return(edges_1)

def table_name_to_ids(df, table, table_ids):
    
    filtered = df

    table_name_filter = table if len(table) > 0 and not (table == '(off)') and not (table == '') else None
    table_id_filter = [x for x in table_ids if x != '(off)']

    if (not (table_name_filter is None)) or (len(table_id_filter) > 0):
        hits = filtered['Table'] == 'no hits'
        if not (table_name_filter is None):
            hits = filtered['Table'].str.contains(table_name_filter, case=False)
        for id in table_id_filter:
            hits = hits | (filtered['Table'] == id)
        filtered = filtered[ hits ]
    
    return(filtered['Table'].unique().tolist())


def node_filtering(nodes,ids):
    nodes = nodes[nodes['z_tableFilter'].str.lower().str.contains('|'.join(ids))]
    return(nodes)

def edge_filtering(edges,ids):
    edges = edges[edges['z_tableFilter'].str.lower().str.contains('|'.join(ids))] 
    return(edges)

def namediff_filtering(df):
    df = df[df['colSim'].str.match('False')] 
    return(df)

def render_url(logger,url):
    logger.debug('rendering main area, with url: %s', url)
    iframe = '<iframe src="' + url + '", height="800", width="100%" allow="fullscreen"></iframe>'
    st.markdown(iframe, unsafe_allow_html=True)

def graphistry_graph(df,lvl1,lvl2,lvl3): 
    graphistry.register(api=3, server="hub.graphistry.com", username=st.secrets["graphistry_username"],  password=st.secrets["graphistry_password"])

    g = graphistry.hypergraph(df, [lvl1, lvl2, lvl3], direct=True, drop_edge_attrs=True,
        opts={
            "EDGES": {
                lvl1: [ lvl2 ],
                lvl2: [ lvl3 ]
            }
        })['graph']

    # Add color and other stuff
    g = g.nodes(node_decorator(g._nodes,lvl1,lvl2,g._edges))#.edges(edge_decorator(g._edges))

    # Node to edge transform
    g = node_to_edge(g,'output','Table.Column')

    #Add data to nodes and remove rows edges that have same Table
    g = g.nodes(node_add_data(df,g._nodes)).edges(edge_rem_data(g._edges))
    return(g)