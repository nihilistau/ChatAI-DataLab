# Workshop Extension Template

## How to Extend Workshop

- Create a new Recipe notebook in `workshop/notebooks/`.
- Add custom widgets in `workshop/widgets/`.
- Add utility scripts in `workshop/scripts/`.

## Example: Custom Recipe
```python
# custom_recipe.py

def custom_recipe():
    print("This is your custom Recipe. Extend and innovate!")

custom_recipe()
```

## Example: Custom Widget
```python
# custom_widget.py
class CustomWidget:
    def display(self):
        print("Custom widget displayed!")
```

## Next Steps
- Document your extension in the README.
- Share your Cookbooks and Recipes with others.
