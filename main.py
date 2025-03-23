import typer
import uvicorn
import asyncio

from moat import server, config, database, models
app_cli = typer.Typer()

@app_cli.command()
def run(reload: bool = False):
    """
    Run the Moat server.
    """
    asyncio.run(database.init_db()) # Initialize database
    uvicorn.run("moat.server:app", host="0.0.0.0", port=8000, reload=reload)

if __name__ == "__main__":
    app_cli()