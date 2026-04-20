import json
import os
import re
import time
from typing import Dict, List, Optional, Tuple

EPSILON = 1e-9
REPEAT_COUNT = 10
SUPPORTED_PERF_SIZES = [3, 5, 13, 25]


class ValidationError(Exception):
    pass


def normalize_label(value: str, source: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"라벨 타입 오류({source}): 문자열이어야 합니다.")

    key = value.strip().lower()
    mapping = {
        "+": "Cross",
        "cross": "Cross",
        "x": "X",
    }

    if key not in mapping:
        raise ValidationError(
            f"라벨 정규화 실패({source}): '{value}'는 지원되지 않는 라벨입니다."
        )

    return mapping[key]


def parse_row_of_numbers(line: str, expected_n: int) -> List[float]:
    tokens = line.strip().split()
    if len(tokens) != expected_n:
        raise ValidationError(
            f"입력 형식 오류: 각 줄에 {expected_n}개의 숫자를 공백으로 구분해 입력하세요."
        )

    row: List[float] = []
    for token in tokens:
        try:
            row.append(float(token))
        except ValueError as exc:
            raise ValidationError(
                "입력 형식 오류: 숫자만 입력해야 합니다."
            ) from exc

    return row


def validate_square_matrix(matrix: List[List[float]], n: int, context: str) -> None:
    if not isinstance(matrix, list) or len(matrix) != n:
        raise ValidationError(
            f"크기 불일치({context}): {n}x{n} 행렬이어야 합니다."
        )

    for i, row in enumerate(matrix):
        if not isinstance(row, list) or len(row) != n:
            raise ValidationError(
                f"크기 불일치({context}): {i + 1}번째 행의 길이가 {n}이 아닙니다."
            )
        for value in row:
            if not isinstance(value, (int, float)):
                raise ValidationError(
                    f"타입 오류({context}): 행렬 원소는 숫자여야 합니다."
                )


def read_matrix_from_console(n: int, title: str) -> List[List[float]]:
    print(title)
    print(f"{n}줄을 입력하세요. 각 줄은 공백으로 구분된 {n}개의 숫자여야 합니다.")

    while True:
        rows: List[List[float]] = []
        failed = False

        for i in range(n):
            line = input(f"[{i + 1}/{n}] ").strip()
            try:
                row = parse_row_of_numbers(line, n)
                rows.append(row)
            except ValidationError as err:
                print(err)
                print("다시 입력해 주세요.")
                failed = True
                break

        if failed:
            continue

        return rows


def print_matrix(matrix: List[List[float]]) -> None:
    for row in matrix:
        print(" ".join(f"{value:g}" for value in row))


def compute_mac(input_matrix: List[List[float]], filter_matrix: List[List[float]]) -> float:
    n = len(input_matrix)
    score = 0.0

    for i in range(n):
        for j in range(n):
            score += input_matrix[i][j] * filter_matrix[i][j]

    return score


def flatten_matrix(matrix: List[List[float]]) -> List[float]:
    flat: List[float] = []
    for row in matrix:
        for value in row:
            flat.append(value)
    return flat


def compute_mac_1d(flat_input: List[float], flat_filter: List[float]) -> float:
    if len(flat_input) != len(flat_filter):
        raise ValidationError("1차원 MAC 크기 불일치")

    score = 0.0
    for i in range(len(flat_input)):
        score += flat_input[i] * flat_filter[i]
    return score


def measure_average_time_ms(callback, repeat: int = REPEAT_COUNT) -> float:
    start = time.perf_counter()
    for _ in range(repeat):
        callback()
    elapsed = time.perf_counter() - start
    return (elapsed / repeat) * 1000.0


def compare_two_scores(score_a: float, score_b: float, epsilon: float = EPSILON) -> str:
    if abs(score_a - score_b) < epsilon:
        return "UNDECIDED"
    return "A" if score_a > score_b else "B"


def judge_label(cross_score: float, x_score: float, epsilon: float = EPSILON) -> str:
    if abs(cross_score - x_score) < epsilon:
        return "UNDECIDED"
    return "Cross" if cross_score > x_score else "X"


def extract_size_from_pattern_key(key: str) -> int:
    match = re.match(r"^size_(\d+)_\d+$", key)
    if not match:
        raise ValidationError(
            f"패턴 키 형식 오류: '{key}' (기대 형식: size_N_idx)"
        )
    return int(match.group(1))


def generate_cross_pattern(n: int) -> List[List[float]]:
    if n <= 0 or n % 2 == 0:
        raise ValidationError("패턴 생성기 오류: N은 양의 홀수여야 합니다.")

    center = n // 2
    matrix = [[0.0 for _ in range(n)] for _ in range(n)]

    for i in range(n):
        matrix[i][center] = 1.0
    for j in range(n):
        matrix[center][j] = 1.0

    return matrix


def generate_x_pattern(n: int) -> List[List[float]]:
    if n <= 0 or n % 2 == 0:
        raise ValidationError("패턴 생성기 오류: N은 양의 홀수여야 합니다.")

    matrix = [[0.0 for _ in range(n)] for _ in range(n)]

    for i in range(n):
        matrix[i][i] = 1.0
        matrix[i][n - 1 - i] = 1.0

    return matrix


def get_data_json_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")


def load_data_json(data_path: str) -> Dict:
    if not os.path.exists(data_path):
        raise ValidationError(f"data.json 파일을 찾을 수 없습니다: {data_path}")

    try:
        with open(data_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
    except json.JSONDecodeError as err:
        raise ValidationError(f"JSON 파싱 오류: {err}") from err

    if not isinstance(data, dict):
        raise ValidationError("JSON 루트는 객체(dict)여야 합니다.")

    if "filters" not in data or "patterns" not in data:
        raise ValidationError("JSON 스키마 오류: filters/patterns 키가 필요합니다.")

    if not isinstance(data["filters"], dict) or not isinstance(data["patterns"], dict):
        raise ValidationError("JSON 스키마 오류: filters/patterns는 객체여야 합니다.")

    return data


def build_filter_bank(raw_filters: Dict) -> Dict[int, Dict[str, List[List[float]]]]:
    filter_bank: Dict[int, Dict[str, List[List[float]]]] = {}

    for size_key, pair in raw_filters.items():
        m = re.match(r"^size_(\d+)$", size_key)
        if not m:
            raise ValidationError(
                f"필터 키 형식 오류: '{size_key}' (기대 형식: size_N)"
            )

        n = int(m.group(1))

        if not isinstance(pair, dict):
            raise ValidationError(f"필터 구조 오류({size_key}): 객체여야 합니다.")

        normalized_pair: Dict[str, List[List[float]]] = {}

        for raw_label, matrix in pair.items():
            label = normalize_label(raw_label, f"filter key {size_key}")
            validate_square_matrix(matrix, n, f"filter {size_key}:{label}")
            normalized_pair[label] = matrix

        if "Cross" not in normalized_pair or "X" not in normalized_pair:
            raise ValidationError(
                f"필터 누락({size_key}): Cross/X 두 필터가 모두 필요합니다."
            )

        filter_bank[n] = normalized_pair

    return filter_bank


def analyze_patterns(
    patterns: Dict,
    filter_bank: Dict[int, Dict[str, List[List[float]]]],
) -> Tuple[int, int, int, List[Tuple[str, str]]]:
    total = 0
    passed = 0
    failed = 0
    failed_cases: List[Tuple[str, str]] = []

    print("#---------------------------------------")
    print("# [2] 패턴 분석 (라벨 정규화 적용)")
    print("#---------------------------------------")

    for key in sorted(patterns.keys()):
        total += 1
        print(f"--- {key} ---")

        try:
            n = extract_size_from_pattern_key(key)
            item = patterns[key]

            if not isinstance(item, dict):
                raise ValidationError("패턴 항목은 객체여야 합니다.")

            if "input" not in item or "expected" not in item:
                raise ValidationError("패턴 항목에 input/expected가 필요합니다.")

            input_matrix = item["input"]
            expected_label = normalize_label(item["expected"], f"expected {key}")

            validate_square_matrix(input_matrix, n, f"pattern {key}")

            if n not in filter_bank:
                raise ValidationError(f"필터 누락: size_{n} 필터가 없습니다.")

            cross_filter = filter_bank[n]["Cross"]
            x_filter = filter_bank[n]["X"]

            validate_square_matrix(cross_filter, n, f"filter size_{n}:Cross")
            validate_square_matrix(x_filter, n, f"filter size_{n}:X")

            cross_score = compute_mac(input_matrix, cross_filter)
            x_score = compute_mac(input_matrix, x_filter)

            predicted = judge_label(cross_score, x_score, EPSILON)
            status = "PASS" if predicted == expected_label else "FAIL"

            print(f"Cross 점수: {cross_score:.16f}")
            print(f"X 점수: {x_score:.16f}")
            print(f"판정: {predicted} | expected: {expected_label} | {status}")

            if status == "PASS":
                passed += 1
            else:
                failed += 1
                if predicted == "UNDECIDED":
                    reason = f"동점 규칙 적용(UNDECIDED), expected={expected_label}"
                else:
                    reason = f"예측 불일치(predicted={predicted}, expected={expected_label})"
                failed_cases.append((key, reason))

        except ValidationError as err:
            failed += 1
            failed_cases.append((key, str(err)))
            print(f"판정: FAIL ({err})")

    return total, passed, failed, failed_cases


def run_performance_analysis(filter_bank: Dict[int, Dict[str, List[List[float]]]]) -> None:
    print("#---------------------------------------")
    print(f"# [3] 성능 분석 (평균/{REPEAT_COUNT}회)")
    print("#---------------------------------------")
    print("크기       평균 시간(ms)    연산 횟수")
    print("-------------------------------------")

    base_rows: List[Tuple[int, float, int]] = []
    bonus_rows: List[Tuple[int, float, float, float]] = []

    for n in SUPPORTED_PERF_SIZES:
        pattern = generate_cross_pattern(n)

        if n in filter_bank:
            cross_filter = filter_bank[n]["Cross"]
        else:
            cross_filter = generate_cross_pattern(n)

        avg_2d_ms = measure_average_time_ms(
            lambda m=pattern, f=cross_filter: compute_mac(m, f), REPEAT_COUNT
        )

        flat_pattern = flatten_matrix(pattern)
        flat_filter = flatten_matrix(cross_filter)
        avg_1d_ms = measure_average_time_ms(
            lambda a=flat_pattern, b=flat_filter: compute_mac_1d(a, b), REPEAT_COUNT
        )

        ops = n * n
        base_rows.append((n, avg_2d_ms, ops))

        speedup = (avg_2d_ms / avg_1d_ms) if avg_1d_ms > 0 else 0.0
        bonus_rows.append((n, avg_2d_ms, avg_1d_ms, speedup))

    for n, ms, ops in base_rows:
        print(f"{n}x{n:<8}{ms:>12.6f}{ops:>14}")

    print()
    print("[보너스] 2D vs 1D MAC 성능 비교")
    print("크기       2D(ms)      1D(ms)      속도비(2D/1D)")
    print("-------------------------------------------------")
    for n, ms2d, ms1d, ratio in bonus_rows:
        print(f"{n}x{n:<8}{ms2d:>10.6f}{ms1d:>12.6f}{ratio:>15.3f}")


def print_result_summary(
    total: int,
    passed: int,
    failed: int,
    failed_cases: List[Tuple[str, str]],
) -> None:
    print("#---------------------------------------")
    print("# [4] 결과 요약")
    print("#---------------------------------------")
    print(f"총 테스트: {total}개")
    print(f"통과: {passed}개")
    print(f"실패: {failed}개")

    if failed_cases:
        print()
        print("실패 케이스:")
        for key, reason in failed_cases:
            print(f"- {key}: {reason}")


def run_mode_user_input() -> None:
    print("#---------------------------------------")
    print("# [1] 필터 입력")
    print("#---------------------------------------")
    filter_a = read_matrix_from_console(3, "필터 A (3줄 입력, 공백 구분)")
    filter_b = read_matrix_from_console(3, "필터 B (3줄 입력, 공백 구분)")

    print("#---------------------------------------")
    print("# [1-1] 필터 저장 확인")
    print("#---------------------------------------")
    print("필터 A 저장 완료:")
    print_matrix(filter_a)
    print("필터 B 저장 완료:")
    print_matrix(filter_b)

    print("#---------------------------------------")
    print("# [2] 패턴 입력")
    print("#---------------------------------------")
    pattern = read_matrix_from_console(3, "패턴 (3줄 입력, 공백 구분)")

    print("#---------------------------------------")
    print("# [3] MAC 결과")
    print("#---------------------------------------")
    score_a = compute_mac(pattern, filter_a)
    score_b = compute_mac(pattern, filter_b)

    decision = compare_two_scores(score_a, score_b, EPSILON)
    avg_ms = measure_average_time_ms(
        lambda p=pattern, a=filter_a, b=filter_b: (
            compute_mac(p, a),
            compute_mac(p, b),
        ),
        REPEAT_COUNT,
    )

    print(f"A 점수: {score_a:.16f}")
    print(f"B 점수: {score_b:.16f}")
    print(f"연산 시간(평균/{REPEAT_COUNT}회): {avg_ms:.6f} ms")

    if decision == "UNDECIDED":
        print(f"판정: 판정 불가 (|A-B| < {EPSILON})")
    else:
        print(f"판정: {decision}")

    print()
    print("#---------------------------------------")
    print(f"# [4] 성능 분석 (3x3, 평균/{REPEAT_COUNT}회)")
    print("#---------------------------------------")
    avg_single_mac_ms = measure_average_time_ms(
        lambda p=pattern, a=filter_a: compute_mac(p, a), REPEAT_COUNT
    )
    print("크기       평균 시간(ms)    연산 횟수")
    print("-------------------------------------")
    print(f"3x3{'' :<8}{avg_single_mac_ms:>12.6f}{(3 * 3):>14}")

    # Bonus comparison on same 3x3 input
    flat_p = flatten_matrix(pattern)
    flat_a = flatten_matrix(filter_a)
    avg_2d = measure_average_time_ms(lambda: compute_mac(pattern, filter_a), REPEAT_COUNT)
    avg_1d = measure_average_time_ms(lambda: compute_mac_1d(flat_p, flat_a), REPEAT_COUNT)
    ratio = (avg_2d / avg_1d) if avg_1d > 0 else 0.0
    print("[보너스] 3x3 2D vs 1D 비교")
    print(f"2D: {avg_2d:.6f} ms | 1D: {avg_1d:.6f} ms | 속도비(2D/1D): {ratio:.3f}")


def run_mode_json_analysis() -> None:
    data_path = get_data_json_path()

    print("#---------------------------------------")
    print("# [1] 필터 로드")
    print("#---------------------------------------")

    data = load_data_json(data_path)
    filter_bank = build_filter_bank(data["filters"])

    for n in sorted(filter_bank.keys()):
        print(f"size_{n} 필터 로드 완료 (Cross, X)")

    total, passed, failed, failed_cases = analyze_patterns(data["patterns"], filter_bank)
    print()
    run_performance_analysis(filter_bank)
    print()
    print_result_summary(total, passed, failed, failed_cases)


def print_menu() -> None:
    print("=== Mini NPU Simulator ===")
    print()
    print("[모드 선택]")
    print("1. 사용자 입력 (3x3)")
    print("2. data.json 분석")


def main() -> None:
    print_menu()
    choice = input("선택: ").strip()

    try:
        if choice == "1":
            run_mode_user_input()
        elif choice == "2":
            run_mode_json_analysis()
        else:
            print("잘못된 선택입니다. 1 또는 2를 입력하세요.")
    except ValidationError as err:
        print(f"오류: {err}")


if __name__ == "__main__":
    main()
