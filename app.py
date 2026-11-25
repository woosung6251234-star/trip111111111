# 실행 버튼
if st.sidebar.button("🚀 여행 최적화 시작하기"):
    with st.spinner("경로와 예산을 분석 중입니다..."):
        
        # --- 🚨 [추가된 예외 처리 로직] 제주도 등 섬 지역 방문 시 ---
        if "제주" in dest_input:
            st.warning("🌴 제주도는 항공편 이용이 필수이므로, TMAP 대신 평균 항공권/렌터카 예산으로 대체 계산합니다.")
            hours, minutes = 1, 10 # 서울-제주 비행시간 약 1시간 10분
            one_way_cost = 80000 # 편도 항공권+공항 이동 비용(임의값)
            start_coord = {"name": origin_input}
            end_coord = {"name": dest_input}
            budget_plan = calculate_budget(total_budget, one_way_cost, days)
            
        else:
            # 기존 TMAP 로직 정상 실행 (육지 이동)
            start_coord = get_coordinates(origin_input)
            end_coord = get_coordinates(dest_input)
            
            if not start_coord or not end_coord:
                st.error("장소를 찾을 수 없습니다. 더 정확한 명칭을 입력해 주세요.")
                st.stop()
                
            route_data = get_route_info(start_coord, end_coord)
            if not route_data:
                st.error("경로 정보를 불러오는 데 실패했습니다.")
                st.stop()
                
            h, remainder = divmod(route_data["total_time_sec"], 3600)
            m, _ = divmod(remainder, 60)
            hours, minutes = h, m
            
            # 여기서 주유비 계산을 택시비가 아닌 더 현실적인 연비 계산으로 바꿀 수도 있습니다.
            one_way_cost = route_data["toll_fee"] + route_data["taxi_fare"] 
            budget_plan = calculate_budget(total_budget, one_way_cost, days)
        # -------------------------------------------------------------
        
        if "error" in budget_plan:
            st.error(budget_plan["error"])
            st.stop()

        # (이하 결과 출력 코드는 동일)
