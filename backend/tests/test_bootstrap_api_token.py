from tools.bootstrap_api_token import build_parser


def test_bootstrap_token_parser():
    args = build_parser().parse_args(["--user-id", "7", "--expires-days", "90"])

    assert args.user_id == 7
    assert args.expires_days == 90
