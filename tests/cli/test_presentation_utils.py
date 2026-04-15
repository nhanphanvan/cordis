from cordis.cli.utils.presentation import print_path_summary


def test_print_path_summary_uses_path_column(capsys) -> None:
    print_path_summary("Downloaded", ["alpha.txt"])

    captured = capsys.readouterr()

    assert "Downloaded" in captured.out
    assert "Path" in captured.out
    assert "alpha.txt" in captured.out
