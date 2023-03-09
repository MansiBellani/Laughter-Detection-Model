import streamlit as st
import pandas as pd
import numpy as np
from prediction import predict
# st.title(Laughter Detection")
st.markdown(‘Toy model to play to classify iris flowers into \
setosa, versicolor, virginica’)

st.button(“Predict type of Iris”)
streamlit run app.py
