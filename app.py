import streamlit as st
import pandas as pd
import requests

# ---------------------------------------------------------
# 1. API 통신 및 예산 계산 로직 (함수 모음)
# ---------------------------------------------------------
def get_coordinates(keyword):
    """TMAP API: 장소명을 위도/경도로 변환"""
    url = "https://apis.openapi.sk.com/tmap/pois"
    headers = {"appKey": st.secrets["TMAP_API_KEY"]}
    params = {
        "version": "1",
        "searchKeyword": keyword,
        "resCoordType": "WGS84GEO",
        "reqCoordType": "WGS84GEO",
        "count": 1
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        if "searchPoiInfo" in data:
            poi = data["searchPoiInfo"]["pois"]["poi"][0]
            return {"name": poi["name"], "lat": poi["frontLat"], "lon": poi["frontLon"]}
    return None

def get_route_info(start_coord, end_coord):
    """TMAP API: 출발/도착지 좌표로 소요 시간 및 요금 조회"""
    url = "https://apis.openapi.sk.com/tmap/routes"
    headers = {
        "accept": "application/json",
        "appKey": st.secrets["TMAP_API_KEY"]
    }
    payload = {
        "startX": start_coord["lon"], "startY": start_coord["lat"],
        "endX": end_coord["lon"], "endY": end_coord["lat"],
        "reqCoordType": "WGS84GEO", "resCoordType": "WGS84GEO",
        "searchOption": "0"
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        properties = response.json()["features"][0]["properties"]
        return {
            "total_time_sec": properties.get("totalTime", 0),
            "toll_fee": properties.get("totalFare", 0),
            "taxi_fare": properties.get("taxiFare", 0) # 주유비 대체
        }
    return None

def calculate_budget(total_budget, one_way_cost, days):
    """예산 분배 로직 (교통비 제외 후 숙박 60%, 식비 40%)"""
    round_trip_cost = one_way_cost * 2
    remaining = total_budget - round_trip_cost
    
    if remaining < 0:
        return {"error": "예산이 필수 교통비보다 적습니다. 총예산을 늘려주세요."}
        
    lodging = int(remaining * 0.6)
    food = int(remaining * 0.4)
    
    return {
        "transport_cost": round_trip_cost,
        "remaining_budget": remaining,
        "lodging_budget": lodging,
        "food_budget": food,
        "daily_lodging": int(lodging / (days - 1)) if days > 1 else lodging,
        "daily_food": int(food / days)
    }

# ---------------------------------------------------------
# 2. 메인 화면 UI 및 실행 흐름
# ---------------------------------------------------------
st.set_page_config(page_title="VibeTravel 플래너", page_icon="✈️", layout="wide")

# 디자인(CSS) 간소화 적용
st.markdown("""
    <style>
    div[data-testid="stMetricValue"] { color: #1f77b4; font-weight: bold; }
    div.stButton > button:first-child { background-color: #ff4b4b; color: white; width: 100%; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 사이드바 (입력 폼)
st.sidebar.header("🎒 여행 조건 설정")
origin_input = st.sidebar.text_input("출발지 검색", "서울역")
dest_input = st.sidebar.text_input("도착지 검색", "해운대해수욕장")
total_budget = st.sidebar.number_input("총예산 (원)", min_value=50000, value=500000, step=50000)
days = st.sidebar.slider("여행 기간 (일)", 1, 7, 2)
theme = st.sidebar.selectbox("여행 테마", ["가성비 짠내투어", "시간절약 최단코스", "여유로운 힐링투어"])

# 메인 헤더
st.title("✈️ VibeTravel: 스마트 동선 & 예산 플래너")
st.markdown("입력하신 조건과 실시간 TMAP 데이터를 바탕으로 최적의 여행 일정을 계산합니다.")

# 실행 버튼
if st.sidebar.button("🚀 여행 최적화 시작하기"):
    with st.spinner("경로와 예산을 분석 중입니다..."):
        
        # 1. API 호출 (좌표 검색)
        start_coord = get_coordinates(origin_input)
        end_coord = get_coordinates(dest_input)
        
        if not start_coord or not end_coord:
            st.error("장소를 찾을 수 없습니다. 더 정확한 명칭을 입력해 주세요.")
            st.stop()
            
        # 2. API 호출 (경로 탐색)
        route_data = get_route_info(start_coord, end_coord)
        if not route_data:
            st.error("경로 정보를 불러오는 데 실패했습니다.")
            st.stop()
            
        # 3. 데이터 가공 및 예산 계산
        hours, remainder = divmod(route_data["total_time_sec"], 3600)
        minutes, _ = divmod(remainder, 60)
        
        one_way_cost = route_data["toll_fee"] + route_data["taxi_fare"]
        budget_plan = calculate_budget(total_budget, one_way_cost, days)
        
        if "error" in budget_plan:
            st.error(budget_plan["error"])
            st.stop()

        # 4. 결과 출력
        st.success(f"✨ **{start_coord['name']}**에서 **{end_coord['name']}**까지의 맞춤형 플랜이 완성되었습니다!")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("🚗 예상 소요 시간 (편도)", f"{hours}시간 {minutes}분")
        col2.metric("💳 필수 교통비 (왕복 통행료+기타)", f"{budget_plan['transport_cost']:,} 원")
        col3.metric("🏨 현지 가용 예산", f"{budget_plan['remaining_budget']:,} 원")
        
        st.divider()
        
        # 5. 하단 탭 리포트
        tab1, tab2 = st.tabs(["📊 상세 예산 리포트", "🗺️ 경로 정보 요약"])
        
        with tab1:
            col_chart, col_text = st.columns([1.5, 1])
            with col_chart:
                chart_data = pd.DataFrame(
                    {"금액": [budget_plan['transport_cost'], budget_plan['lodging_budget'], budget_plan['food_budget']]},
                    index=["왕복 교통비", "숙박비 (60%)", "식비/기타 (40%)"]
                )
                st.bar_chart(chart_data)
            with col_text:
                st.info(f"**테마:** {theme}")
                st.write(f"- 🏨 추천 숙소 가격: **1박 평균 {budget_plan['daily_lodging']:,}원**")
                st.write(f"- 🍽️ 추천 식비 가격: **1일 평균 {budget_plan['daily_food']:,}원**")
                
        with tab2:
            st.markdown(f"### 📍 경로 요약")
            st.write(f"- **출발지:** {start_coord['name']} (위도 {start_coord['lat']}, 경도 {start_coord['lon']})")
            st.write(f"- **도착지:** {end_coord['name']} (위도 {end_coord['lat']}, 경도 {end_coord['lon']})")
