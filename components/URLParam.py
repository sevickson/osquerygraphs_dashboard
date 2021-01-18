import json, streamlit as st, urllib

class URLParam:
    def __init__(self, prefix='d_'):
        self.prefix = prefix

    # str * 'a -> 'a
    def get_field(self, field: str, default=None):
        field = self.prefix + field
        query_params = st.experimental_get_query_params()
        maybe_v = json.loads(urllib.parse.unquote(query_params[field][0])) if field in query_params else None
        out = default if maybe_v is None else maybe_v
        return out

    # str * 'a -> ()
    def set_field(self, field: str, val):
        field = self.prefix + field
        query_params = st.experimental_get_query_params()

        query_params = st.experimental_set_query_params(**{
            **{k: v[0] for k, v in query_params.items()},
            **{field: urllib.parse.quote(json.dumps(val), safe='')}
        })