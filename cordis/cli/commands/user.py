import typer

from cordis.cli.commands.common import get_client, handle_cli_errors, print_detail, print_table, run_async

app = typer.Typer(help="User commands.")


@app.callback()
def user() -> None:
    """User command group."""


@app.command("me")
@handle_cli_errors
def user_me() -> None:
    me = run_async(get_client().get_me())
    print_detail("User", {"ID": me["id"], "Email": me["email"]})


@app.command("ls")
@handle_cli_errors
def list_users_command() -> None:
    items = run_async(get_client().list_users())
    print_table(
        "Users",
        ["ID", "Email", "Admin"],
        [[item["id"], item["email"], item["is_admin"]] for item in items],
    )


@app.command("info")
@handle_cli_errors
def get_user_info(email: str = typer.Option(..., "--email")) -> None:
    item = run_async(get_client().get_user_by_email(email=email))
    print_detail("User", {"ID": item["id"], "Email": item["email"], "Admin": item["is_admin"]})
