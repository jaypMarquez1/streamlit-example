

import streamlit as st
import streamlit_authenticator as sa


auth = sa.Authenticator(
    SECRET_KEY,
    token_url="/token",
    token_ttl=3600,
    password_hashing_method=sa.PasswordHashingMethod.BCRYPT,
)
@auth.login_required
def protected():
    st.write("This is a protected route.")
    
@st.route("/password-reset")
def password_reset():
   
   email = st.text_input("Enter your email address")
   if st.button("Reset Password"):
   
      reset_link = auth.generate_password_reset_link(email)
      
       

    
@st.route("/login")
def login():
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
 
    if st.button("Login"):
        user = auth.authenticate(username, password)
        if user is not None:
            auth.login_user(user)
            st.success("Logged in successfully.")
        else:
            st.error("Invalid username or password.")
            
            
conn = st.experimental_connection("snowpark")
df = conn.query("select current_warehouse()")
st.write(df)

'''import streamlit as st

conn = st.experimental_connection("snowpark")
#if not conn.is_healthy():
   # conn.reset()
    
df = conn.query("select * from FROSTY_SAMPLE.CYBERSYN_FINANCIAL.FINANCIAL_ENTITY_ANNUAL_TIME_SERIES  limit 10;")
st.write(df)
'''
