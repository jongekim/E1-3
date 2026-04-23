# Mini NPU Simulator

## 실행 방법
1. Python 3.8 이상이 설치되어 있어야 합니다.
2. 프로젝트 루트에서 아래 명령으로 실행합니다.

```bash
python main.py
```

3. 모드 선택:
- 1: 사용자 입력 (3x3)
- 2: data.json 분석

4. data.json 위치:
- main.py와 같은 경로에 data.json이 있어야 합니다.

## 구현 요약
- MAC 연산은 외부 라이브러리 없이 반복문으로 직접 구현했습니다.
- 라벨 정규화 정책:
  - expected: + -> Cross, x -> X
  - filter key: cross -> Cross, x -> X
- 동점 정책(epsilon): abs(score_a - score_b) < 1e-9 이면 UNDECIDED 처리합니다.
- 비교 기준은 내부 표준 라벨 Cross/X로 통일했습니다.
- 모드 2에서는 케이스별 검증 실패를 FAIL로 처리하고 전체 실행은 계속합니다.

## 결과 리포트
아래 내용은 본 구현의 설계 기준과 해석 원칙입니다.
1. FAIL 원인은 크게 세 가지로 분리했습니다: 데이터/스키마 문제, 로직 문제, 수치 비교 문제.
2. 데이터/스키마 문제는 대표적으로 패턴 키 형식 오류, input/expected 누락, 크기 불일치입니다.
3. 이 경우 프로그램 전체를 종료하지 않고 해당 케이스만 FAIL로 기록합니다.
4. 로직 문제는 필터 선택 규칙(size_N 매칭) 또는 라벨 정규화 누락에서 발생할 수 있습니다.
5. 이를 줄이기 위해 expected/filter 라벨을 모두 normalize_label 함수로 일원화했습니다.
6. 수치 비교 문제는 부동소수점 오차로 인해 score_a와 score_b가 사실상 같아 보일 때 발생합니다.
7. 이를 해결하기 위해 epsilon 기반 비교를 적용해 UNDECIDED를 명시적으로 반환합니다.
8. expected는 Cross/X만 유효하므로, 판정이 UNDECIDED인 케이스는 현재 정책상 FAIL입니다.
9. 시간 복잡도는 MAC 기준 O(N^2)이며, 각 원소를 정확히 한 번씩 곱하고 누적합니다.
10. 성능 표의 연산 횟수 열(N^2)은 측정 시간 증가와 함께 복잡도 근거를 제공합니다.
11. 보너스 과제로 2D 배열을 1D로 평탄화한 경로를 추가해 동일 O(N^2) 내 상수항 변화를 비교합니다.
12. 패턴 생성기(Cross/X)를 추가해 여러 크기 입력을 재현 가능하게 만들었습니다.

## 보너스 기능
- 2D vs 1D MAC 성능 비교 출력
- 크기 N(양의 홀수)에 대한 Cross/X 패턴 자동 생성

## 함수 이름 기준 MAC 연산 로직 전체 흐름
아래는 실제 코드의 함수 호출 구조를 기준으로 정리한 흐름입니다.

1. 모드 진입
- `main`에서 사용자 선택값에 따라 `run_mode_user_input` 또는 `run_mode_json_analysis`를 호출합니다.

2. 입력/데이터 준비
- `run_mode_user_input`
  - `read_matrix_from_console`로 `filter_a`, `filter_b`, `pattern`을 입력받습니다.
  - 각 줄은 `parse_row_of_numbers`에서 숫자 파싱 및 길이 검증을 수행합니다.
- `run_mode_json_analysis`
  - `load_data_json`으로 `data.json`을 로드합니다.
  - `build_filter_bank`로 크기별 필터 맵을 구성합니다.
  - `analyze_patterns`로 패턴별 판정을 수행합니다.

3. 크기/라벨 정합성 처리 (모드 2)
- `analyze_patterns`
  - `extract_size_from_pattern_key`로 패턴 키(`size_N_idx`)에서 `N`을 추출합니다.
  - `normalize_label`로 expected/filter 라벨을 내부 표준(`Cross`, `X`)으로 정규화합니다.
  - `validate_square_matrix`로 입력/필터 행렬 크기를 검증합니다.
  - 추출한 `N`으로 `filter_bank[N]`을 조회해 동일 크기 필터를 선택합니다.

4. MAC 핵심 계산
- `compute_mac`
  - 이중 루프 `(i, j)`로 같은 위치 원소를 곱합니다.
  - 곱셈 결과를 `score`에 누적 합산합니다.
  - 최종 MAC 점수를 반환합니다.
- 보너스 경로: `flatten_matrix` + `compute_mac_1d`
  - 2D 행렬을 1D로 평탄화한 뒤 동일한 MAC 누적 계산을 수행합니다.

5. 판정
- 모드 1: `compare_two_scores`
  - `A/B` 점수 비교 후 `A`, `B`, `UNDECIDED`를 반환합니다.
- 모드 2: `judge_label`
  - `Cross/X` 점수 비교 후 `Cross`, `X`, `UNDECIDED`를 반환합니다.

6. 시간 측정 경계
- `measure_average_time_ms`
  - 콜백(연산 함수) 실행 구간만 반복 측정합니다.
  - 입력/출력 및 파일 I/O는 측정 경계에서 제외합니다.

7. 결과 출력
- 모드 1(`run_mode_user_input`): A/B 점수, 판정, 평균 시간(ms)을 출력합니다.
- 모드 2(`analyze_patterns`): 패턴별 점수, 판정, expected, PASS/FAIL을 출력합니다.
- `run_performance_analysis`: 크기별 평균 시간(ms), 연산 횟수(N^2)를 출력합니다.
- `print_result_summary`: 총 테스트, 통과, 실패, 실패 케이스를 요약 출력합니다.
