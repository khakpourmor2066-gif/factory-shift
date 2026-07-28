from tools.ci_mvp import build_parser


def test_ci_parser_accepts_artifact_argument():
    parser = build_parser()
    args = parser.parse_args(["--artifact", "artifacts/result.json"])

    assert args.artifact == "artifacts/result.json"
