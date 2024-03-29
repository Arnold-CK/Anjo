import gspread
import streamlit as st
from sqlalchemy import inspect
from sqlalchemy.engine import create_engine

sheet_credentials = st.secrets["sheet_credentials"]
gc = gspread.service_account_from_dict(sheet_credentials)

anjo_sheet = gc.open_by_key(st.secrets["sheet_key"])
worksheet = anjo_sheet.worksheet("Costs")

engine = create_engine(
    "gsheets://",
    service_account_info={
        "type": "service_account",
        "project_id": "anjo-392216",
        "private_key_id": "c762ab15146eda46879585ed770a091a111749f4",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCNVbOlBJpIHx6t\nWPCImPybTHM6ng/lkP5cx6cj9ZFJ4wo3wNMoGl6JNHtpcZW3He9TFE82PHOrW1o3\np63EtILwztFxufrhW7yE5kPHMGLKzefhCfeFmCw+EYWLzp/2d5yb4tMoNFZ//w4y\njwwBdOceo2ij93p9mrjx1hEpPHjuagrPPfzFVYA7CpF2y09/Nr52hKrmULUytqXT\nzMJn09lK8Z0d9wPsx+J+BwTqNnvcA5NyfPX089LWAXAntWXdqpoTm+Jgmv2dX8Wq\nqPCKP4du7JYwdu2qCWfiumMiixICAsRLjIBhU6U5BBv6vkCRGsl8s2JGwOfRgkiV\nWiwIVyiTAgMBAAECggEAEtb5u2WBq1t6m2Dfr1W1Vn46XfXz6IYLYhK7FPAHDfJV\nyljJzO6261MzoDqj2mUDIe/zHyevw4fJ3uFbKH1ndvIauS4xYxj3aD/JiSPKB36r\nCjRp6kT+oMd1Jc3FRPVsytrRiupvHWDCY7rtvsP2iv79U94JVfTp8lK2tuh4tk75\npq/0KNFg5fs+1x/xQFXt0+YXiJI2tbIvxVVNf19+xTR2u0IJ9Y44c3AOLeEdIrph\nzCWzKE0Sj+gQGs50LyE2AnOrUhiAEtE1lKNqolqhkNs6XdeNZx+2ht/U3sghM4lk\nsBNEQ/clDRS4jAZQUMTYehQv+KY74VOqGk10FqK/AQKBgQDDl+2+K/5RZgfPsHY6\nRHtnJVzj4tkl0Iq/oa8Z451FbtH8e+SOUb+aah70XWosjk51ZmbsIsU+J7wc6y1G\ne0HsDESQnw9gNXi4uexZGT6zki+eBpXM5A/qB2yZpOXxORXpxdGfQG47yi/Twt+C\nmfxtA6NqiTyR9+GzAbascg8XBwKBgQC4+/R/g5xKR4bV3c+uEjL0kUZjL0ExYPka\nBPTIuyiQ6LAoJKDXYC9Bdw520q36y5yakuY8DFB9U3f2UTQ5ti1zyDrIrb24RLM6\nt72M9RGXgs9lJKppBGsGknGLpC4Jd/hVjmfDYMvUNc9ttJ8Vb3csriRNopwdXWQ8\nFUruHoVTFQKBgEQbDul9IBzvziB/bWt0lROhaure/oWwS9/WSMZW/1hB8lRcP4Ve\n6by23vhv3pyNILy4X3Yx1USDSXk4WpeEK7wpuWYyPIRfmh2Yf7e2lqKocHQyDs89\nSl1PIH2PcZHBMuQnwYoWQUwIZwbxgCpVvBOphKmAB9s72RcfrZ/2R1LZAoGAMikI\nDIe4mp+4nUePaClBLfYyuvR2Xhhok7iiU8gEYP7nvYrpHl3TkpHhFzFbwfTyWyvY\nSJIiRUmb7uvoGHog6xNxdTc/ibb/Tr3CJXXStl3fNRLzLpTnHJobNf1oCmNAsJpz\n4pPd0YZh3+KpfJuEGlaCO5cLdB797hjr/5PBHV0CgYBmNSDA9WWig3/i4Cv0hpeY\nUdcTlSpT6ER+js5U+AjxGYxktrlQqYyAjcGonayHVWWI987oO1nyx/DL7dhkjB5M\nPt5eyusZMLzqD4iLqf+llMlvMh5XYIjXZFYBy+r2qMeloZfYU9b3TBLC8zFoYmcI\naToTGhtXk9AEgv27btPcWQ==\n-----END PRIVATE KEY-----\n",
        "client_email": "anjo-farm@anjo-392216.iam.gserviceaccount.com",
        "client_id": "114366236137756426516",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/anjo-farm%40anjo-392216.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com",
    },
    catalog={
        "cost_sheet": "https://docs.google.com/spreadsheets/d/1VEuh5jo0ucQIcBn-ZTNNQwV-XcHrssF_HdigEWDjsrw/edit?pli=1#gid=0",
    },
)
inspector = inspect(engine)
print(inspector.get_table_names())

# connection = engine.connect()

# connection = connect(":memory:")
# cursor = connection.cursor()

# query = "SELECT Item FROM cost_sheet"
# for row in connection.execute(query):
#     print("here")
