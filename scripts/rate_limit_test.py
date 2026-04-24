import argparse
import sys
import time
from typing import List, Optional

import httpx


DEFAULT_QUESTIONS = [
    "Hi",
    "How do I log into EPIS?",
    "How do I find a patient by MRN?",
    "How do I create a new OPD visit?",
    "How do I add a diagnosis?",
    "How do I prescribe a medication?",
    "How do I print a prescription?",
    "How do I order lab tests?",
    "How do I discharge a patient?",
    "Where is the Dialysis Dashboard?",
]


def load_questions(path: Optional[str]) -> List[str]:
    if not path:
        return list(DEFAULT_QUESTIONS)

    questions: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            q = line.strip()
            if not q or q.startswith("#"):
                continue
            questions.append(q)

    if not questions:
        raise ValueError("Questions file is empty (or only comments/blank lines).")
    return questions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send questions to the /chat endpoint to validate Redis rate limiting.",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:9000/chat",
        help="Chat endpoint URL (default: http://localhost:9000/chat)",
    )
    parser.add_argument(
        "--client-id",
        default="rate-limit-test",
        help="Value for X-Client-ID header (default: rate-limit-test)",
    )
    parser.add_argument(
        "--questions-file",
        help="Path to a text file with one question per line (blank lines / #comments ignored).",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Repeat the full question list N times (default: 1).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Delay (seconds) between requests (default: 0).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Request timeout seconds (default: 10).",
    )
    parser.add_argument(
        "--read-body",
        action="store_true",
        help="Read the response body (slower; not needed just to see 429/headers).",
    )
    parser.add_argument(
        "--stop-on-429",
        action="store_true",
        help="Stop as soon as a 429 is received.",
    )

    args = parser.parse_args()

    try:
        questions = load_questions(args.questions_file)
    except Exception as e:
        print(f"Failed to load questions: {e}", file=sys.stderr)
        return 2

    questions = questions * max(1, args.repeat)

    headers = {
        "Content-Type": "application/json",
        "X-Client-ID": args.client_id,
    }

    print(f"URL: {args.url}")
    print(f"X-Client-ID: {args.client_id}")
    print(f"Total requests: {len(questions)} (repeat={args.repeat})")
    print(f"Delay: {args.delay}s | Timeout: {args.timeout}s | Read body: {args.read_body}")
    print()

    with httpx.Client(timeout=args.timeout) as client:
        for i, question in enumerate(questions, start=1):
            if args.delay > 0:
                time.sleep(args.delay)

            t0 = time.perf_counter()
            try:
                with client.stream(
                    "POST",
                    args.url,
                    headers=headers,
                    json={"query": question},
                ) as resp:
                    elapsed_ms = int((time.perf_counter() - t0) * 1000)

                    limit = resp.headers.get("x-ratelimit-limit")
                    remaining = resp.headers.get("x-ratelimit-remaining")
                    retry_after = resp.headers.get("retry-after")
                    client_remaining = resp.headers.get("x-ratelimit-client-remaining")
                    ip_remaining = resp.headers.get("x-ratelimit-ip-remaining")

                    print(
                        f"[{i:03}/{len(questions):03}] {resp.status_code} in {elapsed_ms}ms"
                        f" | remaining={remaining}/{limit}"
                        f" | client_rem={client_remaining} ip_rem={ip_remaining}"
                        f"{' | retry-after=' + retry_after if retry_after else ''}"
                    )

                    if args.read_body:
                        _ = resp.read()

                    if resp.status_code == 429 and args.stop_on_429:
                        return 0

            except httpx.RequestError as e:
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                print(f"[{i:03}/{len(questions):03}] ERROR in {elapsed_ms}ms: {e}", file=sys.stderr)
                return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

