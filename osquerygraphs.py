import pandas as pd, streamlit as st
from components.URLParam import URLParam
from components.css import all_css
from components import gfunctions as gf
from pathlib import Path

############################################
#
#   PIPELINE PIECES
#
############################################

app_id = 'osquerygraphs'
urlParams = URLParam(app_id)


#TODO add more text to dashboard
#TODO add markdown file import that can be expanded
#TODO add usage to streamlit sidebar how to select OS and tables and tell when use dispere graph

# Have fun!
def custom_css():
    all_css()
    st.markdown(
        """<style>
        
        </style>""",unsafe_allow_html=True)

#Source: https://pmbaumgartner.github.io/streamlitopedia/markdown.html#using-markdown-files
@st.cache
def read_markdown_file(markdown_file):
    return Path(markdown_file).read_text()

# Given URL params, render left sidebar form and return combined filter settings
#https://docs.streamlit.io/en/stable/api.html#display-interactive-widgets
def sidebar_area():
    with st.sidebar:
        #st.title('Osquery Table Visualizer')
        #https://discuss.streamlit.io/t/how-do-i-align-st-title/1668/5
        st.markdown("<h1 style='text-align: center; color: purple;'>Osquery Table Visualizer</h1>", unsafe_allow_html=True)
        
        usage_markdown = read_markdown_file("usage.md")
        with st.beta_expander("☑ Usage"):
            st.markdown(usage_markdown, unsafe_allow_html=True)

        os_choice = st.radio('Operating System', ['Windows','Linux','MacOS'])

        if os_choice == 'Windows':
            data_df = fetch_data('https://raw.githubusercontent.com/sevickson/Osquery_Data_Graph/master/Data/data_intersect_graphs_windows_hashed_PERC.csv')
        elif os_choice == 'Linux':
            data_df = fetch_data('https://raw.githubusercontent.com/sevickson/Osquery_Data_Graph/master/Data/data_intersect_graphs_linux_hashed_PERC.csv')
        elif os_choice == 'MacOS':
            data_df = fetch_data('https://raw.githubusercontent.com/sevickson/Osquery_Data_Graph/master/Data/data_intersect_graphs_macos_hashed_PERC.csv')

        tables = pd.concat([ data_df['Table'] ]).unique()
        tables.sort()
        #table_ids = st.multiselect('Show Tables with connections (remove (off) to enable filter)', ['(off)'] + tables.tolist())
        table_ids = st.multiselect('Show Osquery tables with connections', tables.tolist())
        
        #Check later if needed
        #t_init = urlParams.get_field('T', '')
        #table_like = st.text_input('Show Tables with name like', t_init)
        #urlParams.set_field('T', table_like)
        #TEMP for here above
        table_like = ''

        name_diff = st.checkbox('Show connected Osquery table columns with different names (Possible naming inconsistencies)')
        
        with st.beta_expander("⚙️ Graph Options"):
            # Checkbox to remove the radius lock, good for further zooming in after a select
            disperse = st.checkbox('Disperse Graph')
            # Dark mode
            dark_mode = st.checkbox('Dark Mode')
            # Expert mode adds menu to the graph in graphistry
            expert_mode = st.checkbox('Expert Mode')
        
        btn = st.button("Why Not❕🎈")
        if btn:
            st.balloons()

    return {'num_nodes': 1000000, 'num_edges': 1000000, 'table_like': table_like, 'table_ids': table_ids, 'os_choice': os_choice, 'data_csv_df': data_df, 'disperse' : disperse, 'dark_mode': dark_mode, 'name_diff': name_diff, 'expert_mode': expert_mode}

@st.cache(suppress_st_warning=True, allow_output_mutation=True, hash_funcs={pd.DataFrame: lambda _: None})
def fetch_data(url):
    df_r = pd.read_csv(url)
    return(df_r)

def table_names_selected(df, table, table_ids):
    
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
    
    return(filtered)

def node_filtering(nodes,ids):
    # Regex to check for Table or Table.Column from this specific table
    ids_re = ['(^|\s)' + s + '(.|$)' for s in ids ]
    nodes = nodes[nodes['z_tableFilter'].str.lower().str.contains('|'.join(ids_re), regex=True)]#'|'.join(ids), regex=False)]
    return(nodes)

def edge_filtering(edges,ids):
    # Regex to check for Table or Table.Column from/to this specific table
    ids_re = ['::' + s + '(.|$)' for s in ids ]
    edges = edges[edges['z_tableFilter'].str.lower().str.contains('|'.join(ids_re), regex=True)] 
    return(edges)

@st.cache(suppress_st_warning=True, allow_output_mutation=True, hash_funcs={pd.DataFrame: lambda _: None})
def run_filters(num_nodes, num_edges, table_like, table_ids, data_csv_df, disperse, os_choice,dark_mode,name_diff,expert_mode):
    #Get data
    data_df_split = gf.m(data_csv_df,'intersect')

    lvl1, lvl2, lvl3 = 'Table', 'Table.Column', 'output'
    ids = gf.z(data_df_split, table_like, table_ids)

    g = gf.n(data_df_split, lvl1, lvl2, lvl3)

    # Add color
    # Colors from Osquery logo #a596ff and #00125f
    g = g.encode_point_color('type', categorical_mapping={lvl1:'#a596ff',lvl2:'#00125f'})
    g = g.encode_edge_color('edgeType', ['#4a9dff','#6f749a'], as_continuous=True)
    
    ## Function to filter based on ids for nodes and edges
    # only enter if the length of ids is not all the tables and not off or empty
    if len(ids) < data_df_split['Table'].nunique() and not any("(off)" in s for s in table_ids) and not (ids == ''):
        #g = g.nodes(gf.P(g._nodes,ids)).edges(gf.j(g._edges,ids))
        g = g.nodes(node_filtering(g._nodes,ids)).edges(edge_filtering(g._edges,ids))

    # Add url params settings
    g = g.settings(url_params={'play':'5000','showArrows':'false','edgeCurvature':0.02,'edgeOpacity':0.1,'lockedR':'true','dissuadeHubs':'true','linLog':'true','pointSize': 3,'bg':'white','labelBackground':'%234A4A4A','menu':'false'})
    
    if disperse:
        g = g.settings(url_params={'lockedR':'false'})
    
    if dark_mode:
        g = g.settings(url_params={'bg':'%23323238'})
    
    if name_diff:
        #pruneOrphans is not working will wait for fix
        g = g.edges(gf.w(g._edges)).encode_edge_color('edgeType', ['#6f749a'], as_categorical=True)#.settings(url_params={'pruneOrphans':'true'})        
    
    if expert_mode:
        g = g.settings(url_params={'menu':'true'})

    # Bind options
    g = g.bind(point_title ='node_title', point_x='radius', point_y=0)
    # Styling options
    title = 'Osquery Table Visualizer'

    # Render graph object
    graph_url = g.name(title).plot(render=False, as_files=True)
    return { 'nodes_df': g._nodes, 'edges_df': g._edges, 'graph_url': graph_url}

def split_column(df,split_column):
    temp_table = df[split_column].str.split(".", n = 1, expand = True)
    df['Table'] = temp_table[0]
    df['Column'] = temp_table[1]
    df_join = df[['Table','Column']]
    return(df_join)

def render_url(url):
    iframe = '<iframe src="' + url + '", height="800", width="100%" allow="fullscreen"></iframe>'
    st.markdown(iframe, unsafe_allow_html=True)
    
def main_area(num_nodes, num_edges, table_like, table_ids, nodes_df, edges_df, graph_url, os_choice, data_csv_df, disperse,dark_mode,name_diff,expert_mode):
    
    #Source: https://pmbaumgartner.github.io/streamlitopedia/markdown.html#using-markdown-files
    intro_markdown = read_markdown_file("intro.md")
    with st.beta_expander("🕸 Graph Info 🕸"):
        st.markdown(intro_markdown, unsafe_allow_html=True)

        c1, c2 = st.beta_columns(2)
        with c1:
            st.video("https://vimeo.com/502806993")
            st.video("https://vimeo.com/502565608")
        with c2:
            st.video("https://vimeo.com/502381798")
            st.video("https://vimeo.com/502815799")
            
    # Display the graph!
    #st.write(graph_url)
    render_url(graph_url)

    st.markdown('If there is an issue with the Graph rendering or the data, just hit __`F5`__🔃.')

    with st.beta_expander("📃 Data Explorer 📃"):
        st.subheader('Selected Osquery Tables')
        #Source: https://github.com/streamlit/streamlit/issues/641
        # .assign(hack='').set_index('hack')
        selected = table_names_selected(data_csv_df, table_like, table_ids)
        selection = ['Table','Column','Column_Total','Column_Join','Percent_Join']
        st.dataframe((selected[selection].drop_duplicates(keep='last').assign(hack='').set_index('hack')))

        #st.subheader('Surrounding columns')
        #st.dataframe(nodes_df['Table.Column'].unique())
        #st.subheader('Surrounding connections')
    #not working
    #st.write(pd.unique(edges_df['src','dst']]))
    #st.write(edges_df.groupby(['src','dst']).unique())

    with st.beta_expander("🚫 Table/Column Exclusions"):
            if os_choice == 'Windows':
                st.subheader(os_choice)
                st.write('Just a quick search to spare you from searching for an Osquery table column combination that has been filtered out.')
                
                # Get the filter list and split the list
                excl_df = pd.DataFrame(pd.read_csv('https://raw.githubusercontent.com/sevickson/Osquery_Data_Graph/master/Data/table_column_exclude_w.csv',header=None))
                excl_df.columns = ['Table']
                excl_df_split = split_column(excl_df,'Table')
                
                # Create multiselect to search it easily
                tables_filt = excl_df_split['Table'].drop_duplicates()
                tables_filt_ms = st.multiselect('',tables_filt.tolist())
                
                if tables_filt_ms:
                    temp_b = excl_df_split.Table.isin(tables_filt_ms)
                    filtered = excl_df_split[temp_b]
                    st.dataframe(filtered.assign(hack='').set_index('hack'))
                #elif os_choice == 'Linux':
                    #data_df = fetch_data('')
                #elif os_choice == 'MacOS':
                    #data_df = fetch_data('')

############################################
#
#   PIPELINE FLOW
#
############################################
def run_all():
    st.set_page_config(page_title='Osquery Table Visualizer', page_icon='https://raw.githubusercontent.com/osquery/osquery-site/source/public/favicons/favicon-32x32.png', layout='wide', initial_sidebar_state='auto') #layout='centered'

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
