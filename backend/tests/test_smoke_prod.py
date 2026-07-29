from tools.smoke_prod import build_parser


def test_smoke_parser_accepts_api_token_without_exposing_it():
    args = build_parser().parse_args(["--api-token", "secret-value", "--skip-bot"])

    assert args.api_token == "secret-value"
    assert args.skip_bot is True
