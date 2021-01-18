import pandas as pd, streamlit as st
from components.URLParam import URLParam
from components.css import all_css
import gfunctions as gf

############################################
#
#   PIPELINE PIECES
#
############################################

app_id = 'osquerygraphs'
urlParams = URLParam(app_id)

# Have fun!
def custom_css():
    all_css()
    st.markdown(
        """<style>
        
        </style>""",unsafe_allow_html=True)

# Given URL params, render left sidebar form and return combined filter settings
#https://docs.streamlit.io/en/stable/api.html#display-interactive-widgets
def sidebar_area():
    with st.sidebar:

        st.markdown('Data retrieved from [Osquery Data Graph](https://github.com/sevickson/Osquery_Data_Graph)')

        os_choice = st.radio('Operating System', ['Windows','Linux','MacOS'])

        if os_choice == 'Windows':
            data_df = fetch_csv('https://raw.githubusercontent.com/sevickson/Osquery_Data_Graph/master/Data/data_intersect_graphs_windows_hashed_PERC.csv')
        elif os_choice == 'Linux':
            data_df = fetch_csv('https://raw.githubusercontent.com/sevickson/Osquery_Data_Graph/master/Data/data_intersect_graphs_linux_hashed_PERC.csv')
        elif os_choice == 'MacOS':
            data_df = fetch_csv('https://raw.githubusercontent.com/sevickson/Osquery_Data_Graph/master/Data/data_intersect_graphs_macos_hashed_PERC.csv')

        tables = pd.concat([ data_df['Table'] ]).unique()
        tables.sort()
        table_ids = st.multiselect('Show Tables with connections (remove (off) to enable filter)', ['(off)'] + tables.tolist())
        
        t_init = urlParams.get_field('T', '')
        table_like = st.text_input('Show Tables with name like', t_init)
        urlParams.set_field('T', table_like)

        name_diff = st.checkbox('Show connected Table columns with different names (Possible naming inconsistencies)')

        # Checkbox to remove the radius lock, good for further zooming in after a select
        disperse = st.checkbox('Disperse Graph')
        # Dark mode
        dark_mode = st.checkbox('Dark Mode')
        # Expert mode adds menu to the graph in graphistry
        expert_mode = st.checkbox('Expert Mode')
        
    return {'num_nodes': 1000000, 'num_edges': 1000000, 'table_like': table_like, 'table_ids': table_ids, 'os_choice': os_choice, 'data_csv_df': data_df, 'disperse' : disperse, 'dark_mode': dark_mode, 'name_diff': name_diff, 'expert_mode': expert_mode}

@st.cache(suppress_st_warning=True, allow_output_mutation=True, hash_funcs={pd.DataFrame: lambda _: None})
def fetch_csv(url):
    df_r = pd.read_csv(url)
    return(df_r)

@st.cache(suppress_st_warning=True, allow_output_mutation=True, hash_funcs={pd.DataFrame: lambda _: None})
def run_filters(num_nodes, num_edges, table_like, table_ids, data_csv_df, disperse, os_choice,dark_mode,name_diff,expert_mode):
    #Get data
    data_df_split = gf.m(data_csv_df,'intersect')

    lvl1, lvl2, lvl3 = 'Table', 'Table.Column', 'output'
    ids = gf.z(data_df_split, table_like, table_ids)

    g = gf.n(data_df_split, lvl1, lvl2, lvl3)

    # Add color
    #g = g.encode_point_color('type', categorical_mapping={lvl1:'rgb(228,26,28)',lvl2:'rgb(55,126,184)',lvl3:'rgb(77,175,74)'}) 
    # Colors from Osquery logo #a596ff and #00125f
    g = g.encode_point_color('type', categorical_mapping={lvl1:'#a596ff',lvl2:'#00125f'})
    
    #g = g.encode_edge_color('edgeType', ['rgb(102,194,165)', 'rgb(252,141,98)'], as_continuous=True)
    #g = g.encode_edge_color('edgeType', ['#4a9dff','#b35346'], as_continuous=True)
    g = g.encode_edge_color('edgeType', ['#4a9dff','#6f749a'], as_continuous=True)
    
    ## Function to filter based on ids for nodes and edges
    # only enter if the length of ids is not all the tables and not off or empty
    if len(ids) < data_df_split['Table'].nunique() and not any("(off)" in s for s in table_ids) and not (ids == ''):
        g = g.nodes(gf.P(g._nodes,ids)).edges(gf.j(g._edges,ids))

    # Add url params settings
    g = g.settings(url_params={'play':'5000','showArrows':'false','edgeCurvature':0.02,'edgeOpacity':0.1,'lockedR':'true','dissuadeHubs':'true','pointSize': 3,'bg':'white','labelBackground':'%234A4A4A','menu':'false'})
    
    if disperse:
        g = g.settings(url_params={'lockedR':'false'})
    
    if dark_mode:
        g = g.settings(url_params={'bg':'%23323238'})
    
    if name_diff:
        g = g.edges(gf.w(g._edges))
    
    if expert_mode:
        g = g.settings(url_params={'menu':'false'})

    # Bind options
    g = g.bind(point_title ='node_title', point_x='radius', point_y=0)
    # Styling options
    title = 'Osquery Table Visualizer'

    # Render graph object
    graph_url = g.name(title).plot(render=False, as_files=True)
    return { 'nodes_df': g._nodes, 'edges_df': g._edges, 'graph_url': graph_url}

def render_url(url):
    iframe = '<iframe src="' + url + '", height="800", width="100%" allow="fullscreen"></iframe>'
    st.markdown(iframe, unsafe_allow_html=True)
    
def main_area(num_nodes, num_edges, table_like, table_ids, nodes_df, edges_df, graph_url, os_choice, data_csv_df, disperse,dark_mode,name_diff,expert_mode):
    # Display the graph!
    render_url(graph_url)

    #st.write(table_ids)
    st.subheader('Selected tables')
    st.write(data_csv_df.head(10))
    st.subheader('Surrounding columns')
    st.write(nodes_df['Table.Column'].unique())
    st.subheader('Surrounding connections')
    #not working
    #st.write(pd.unique(edges_df['src','dst']]))
    #st.write(edges_df.groupby(['src','dst']).unique())

############################################
#
#   PIPELINE FLOW
#
############################################
def run_all():

    custom_css()

    try:
        # Render sidebar and get current settings
        sidebar_filters = sidebar_area()

        # Compute filter pipeline (with auto-caching based on filter setting inputs)
        # Selective mark these as URL params as well
        filter_pipeline_result = run_filters(**sidebar_filters)

        # Render main viz area based on computed filter pipeline results and sidebar settings
        main_area(**sidebar_filters, **filter_pipeline_result)

    except Exception as exn:
        st.write('Error loading dashboard')
        st.write(exn)

# Run the app, create the dashboard
run_all()
