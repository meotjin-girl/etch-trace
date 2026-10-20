# PHM 2018 데이터 사전 (출처: PHM Society Data Challenge 2018 공식 설명서)

## 데이터 구성
train 폴더의 CSV 하나가 이온 밀 식각 장비(Tool) 한 대의 센서 시계열이다. 한 행은 한 측정 시점이며 약 4초 간격으로 기록된다. train_faults 폴더에는 고장 발생 시각(time, fault_name, Tool)이 있다. 데이터는 익명화되어 단위가 제공되지 않으며, 센서값은 표준화(평균 0, 분산 1 근처)된 값이다.

## 식별 컬럼
time: 시각(초). Tool: 장비 ID. stage: 웨이퍼의 공정 단계. Lot: 웨이퍼 ID. runnum: 장비가 실행된 횟수(여러 Lot을 묶은 배치). recipe: 웨이퍼 처리에 사용된 장비 설정 묶음. recipe_step: recipe 안의 공정 단계. 본 시스템은 runnum과 Lot을 합친 run_id('{runnum}-{Lot}')를 조사 단위로 사용하며, 이 단위 안에서 recipe는 하나다.

## 챔버·빔 센서
IONGAUGEPRESSURE: 진공 상태 메인 공정 챔버의 압력 측정값(센서). ETCHBEAMVOLTAGE: 그리드 어셈블리의 빔 플레이트에 인가된 전압. ETCHBEAMCURRENT: 빔 그리드에 닿는 이온 전류로, 그리드를 통과해 웨이퍼로 가속되는 이온 양을 결정한다. ETCHSUPPRESSORVOLTAGE: 서프레서 플레이트에 인가된 전압. ETCHSUPPRESSORCURRENT: 서프레서 그리드 플레이트에 닿는 이온 전류(센서).

## 냉각(FlowCool) 센서
FLOWCOOLFLOWRATE: 질량유량제어기(MFC)가 제어하는 FlowCool 회로의 헬륨 유량. FLOWCOOLPRESSURE: FlowCool 회로에 형성된 헬륨 압력(센서).

## 가스·고정구 센서
ETCHGASCHANNEL1READBACK: 진공 챔버 소스 어셈블리로 들어가는 아르곤 유량. ETCHPBNGASREADBACK: PBN 어셈블리로 들어가는 아르곤 유량. FIXTURETILTANGLE: 웨이퍼 기울기 각도 설정. ROTATIONSPEED: 웨이퍼 회전 속도 설정. ACTUALROTATIONANGLE: 측정된 웨이퍼 회전 각도(센서). FIXTURESHUTTERPOSITION: 웨이퍼 차폐 셔터 열림/닫힘 설정. ACTUALSTEPDURATION: 해당 step의 실제 소요 시간(센서).

## 소모품 카운터
ETCHSOURCEUSAGE: 그리드 어셈블리 소모품 사용 카운터. ETCHAUXSOURCETIMER, ETCHAUX2SOURCETIMER: 챔버 실드 소모품 사용 카운터. 누적값이므로 시간이 지나면 증가하는 것이 정상이며 run 간 편차 비교 대상이 아니다.

## 고장 유형과 주의사항
고장은 세 종류다: FlowCool Pressure Dropped Below Limit, Flowcool Pressure Too High Check Flowcool Pump, Flowcool leak. 기록된 고장 시각은 운영자가 정비를 위해 장비를 정지한 시각이며, 실제 고장 시작은 훨씬 이전일 수 있고 그 시각은 제공되지 않는다. 따라서 고장 기록 시각을 고장 시작 시점으로 단정하면 안 된다.
