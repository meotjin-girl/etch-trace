# 배포 가이드

## 자동 배포 흐름
develop 브랜치에 PR이 머지되면 GitHub Webhook → Jenkins(EC2) → deploy.sh 순서로 자동 배포된다.

## 서버 구성 (EC2, Ubuntu 24.04)
- ~/etch-trace-develop : 배포용 코드 원본 (항상 develop, 수정 파일 없이 유지)
- ~/etch-trace-deploy  : 운영 설정, 비밀값(.env), 배포 스크립트, DB 백업
- ~/etch-trace-work    : 서버에서 작업이 필요할 때 쓰는 작업용 폴더

## deploy.sh가 하는 일
1. develop 최신 코드 pull
2. prepare.py로 운영용 설정 생성
3. DB 백업 (etch-trace-deploy/backups)
4. 이미지 빌드 후 컨테이너 교체, 헬스체크

## 주의
- 서버의 etch-trace-develop 폴더에서 브랜치 변경/파일 수정 금지 (배포 실패 원인)
- 배포 결과는 Jenkins 콘솔 출력에서 확인
- `prometheus` 서비스도 함께 배포된다(호스트 포트 없음). 수집 대상은 `backend/prometheus/targets.json`(모의 장비 EC2 collector)이며, backend는 `prometheus:9090` 경보로 Agent Server 조사(thread·run)를 시작한다. 끄려면 운영 `.env`에 `PROMETHEUS_URL=`
