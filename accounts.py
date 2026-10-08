"""Local sign-in gate and session cleanup."""
import sqlite3
import streamlit as st
from storage import register, authenticate
from design import page_intro


def current_user_id():
    return st.session_state.get('user', {}).get('id')


def _login(user):
    st.session_state.clear()
    st.session_state['user'] = user
    st.rerun()


def require_account():
    if current_user_id():
        return
    page_intro('Your personal study space', 'Welcome to Scripture.',
               'Sign in to keep your studies, personal notes, and verse practice together.')
    signin, signup = st.tabs(['Sign in', 'Create account'])
    with signin:
        with st.form('signin'):
            username = st.text_input('Username', key='login_username', max_chars=32)
            password = st.text_input('Password', type='password', key='login_password', max_chars=256)
            submitted = st.form_submit_button('Sign in →', type='primary')
        if submitted:
            try:
                user = authenticate(username,password)
                if user:
                    _login(user)
                else:
                    st.error('The username or password is incorrect.')
            except (sqlite3.Error, OSError):
                st.error('Could not open your saved data. Check that your data folder is writable.')
    with signup:
        with st.form('signup'):
            username = st.text_input('Choose a username', max_chars=32)
            password = st.text_input('Choose a password', type='password', max_chars=256)
            confirmation = st.text_input('Confirm password', type='password', max_chars=256)
            submitted = st.form_submit_button('Create my account →', type='primary')
        if submitted:
            try:
                if password != confirmation:
                    raise ValueError('The passwords do not match.')
                _login(register(username,password))
            except ValueError as error:
                st.warning(str(error))
            except (sqlite3.Error, OSError):
                st.error('Could not create the account. Check that your data folder is writable.')
    st.caption('Accounts save to this app’s storage. This version has no email sign-in or password recovery. Hosted trials may reset saved data; export important work.')
    st.stop()


def account_sidebar():
    with st.sidebar:
        st.caption(f"Signed in as {st.session_state['user']['username']}")
        if st.button('Sign out'):
            st.session_state.clear()
            st.rerun()
