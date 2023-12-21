import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title='Product Recommendation', page_icon='⚖️', layout="centered", initial_sidebar_state="auto", menu_items=None)

st.caption('VACAYZEN')
st.title('Product Recommendation')
st.info('A tool to suggest the recommended inventory for each asset.')

file_ral       = st.file_uploader('Rental Agreement Lines (RAL_AssetToRentalAgreement)','csv')
file_cost      = st.file_uploader('Cost Per Product (Cost Per Product - CPP)','csv')
file_inventory = st.file_uploader('Inventory (Inventory)','csv')

if file_ral is not None and file_cost is not None and file_inventory is not None:
    st.divider()

    st.toast('Reading uploaded files...')
    df  = pd.read_csv(file_ral)
    cpp = pd.read_csv(file_cost)
    inv = pd.read_csv(file_inventory)

    st.subheader('Date Range')
    st.toast('Determining date range...')

    l, r       = st.columns(2)
    start      = l.date_input('Start', pd.to_datetime('1/1/' + str(pd.to_datetime('today').year)))
    end        = r.date_input('End',   pd.to_datetime('12/31/' + str(pd.to_datetime('today').year)), min_value=start)
    date_range = pd.date_range(start, end)

    df.RentalAgreementReservationStartDate = pd.to_datetime(df.RentalAgreementReservationStartDate).dt.normalize()
    df.RentalAgreementReservationEndDate   = pd.to_datetime(df.RentalAgreementReservationEndDate).dt.normalize()

    st.divider()

    st.subheader('Product of Interest')
    st.toast('Fetching asset data...')

    l, r            = st.columns(2)
    option_category = l.selectbox('Category', df.Product.sort_values().unique())
    df              = df[df.Product == option_category]
    option          = r.selectbox('Asset', df.Description.sort_values().unique())
    df              = df[df.Description == option]
    df              = df[df.RentalStage != 'Cancel']
    df              = df.dropna(subset=['RentalAgreementReservationStartDate','RentalAgreementReservationEndDate'])

    st.toast(f'{option}...')

    def get_cost_to_acquire(row):
        if not pd.isna(row.Unit_Cost):                 return row.Unit_Cost
        elif not pd.isna(row.Last_Analysis_Unit_Cost): return row.Last_Analysis_Unit_Cost
        return 0
    
    st.toast('Determining acquisition cost...')
    cpp['Acquire']  = cpp.apply(get_cost_to_acquire, axis=1)
    cpp             = cpp[cpp.Description == option].reset_index(drop=True)

    rate_acquire    = l.number_input('Cost to Acquire', value=cpp.Acquire[0])
    rate_rent       = r.number_input('Cost to Rent')

    st.divider()

    results = {}

    for day in date_range:
        temp = df[(df.RentalAgreementReservationStartDate <= day) & (df.RentalAgreementReservationEndDate >= day)]
        results[str(day)] = temp.Quantity.sum()

    results = pd.DataFrame.from_dict(results, orient='index', columns=['Quantity'])
    result  = {}

    for i in range(1, results.max()[0]):
        result[i] = len(results[results['Quantity'] >= i])

    result = pd.DataFrame.from_dict(result, orient='index', columns=['Rented'])
    result = result.rename_axis(option)
    result = result.sort_index()

    st.toast('Calculating revenue...')
    result['Revenue'] = rate_rent * result.Rented

    st.toast('Calculating cost...')
    result['Cost']    = rate_acquire

    st.subheader('Recommendation Analysis')
    st.toast('Calculating recommendation...')

    inv = inv[inv.Description == option].reset_index(drop=True)

    l, m, r  = st.columns(3)
    l.metric('Most Rented', result.index.max())
    m.metric('Current Inventory', np.sum(inv.CurrentAssignedQuantity))
    r.metric('Recommended', result[result.Revenue >= rate_acquire].index.max(), int(result[result.Revenue >= rate_acquire].index.max() - np.sum(inv.CurrentAssignedQuantity)))
    l.metric('Revenue', np.sum(result.Revenue))

    st.toast('Adding highlights...')

    def highlight_revenue(value):
        if value >= rate_acquire:
            color = '#50C878'
        else:
            color = '#DE3163'
        return f'background-color: {color}'

    result = result.style.applymap(highlight_revenue, subset=['Revenue'])

    st.dataframe(result, use_container_width=True)