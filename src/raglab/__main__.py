try:
    from raglab.cli import app
    app()
except ImportError:
    print("RagLab CLI is still under development. The cli module will be available in a future release.")
except Exception as e:
    print(f"An error occurred while running RagLab: {e}")
