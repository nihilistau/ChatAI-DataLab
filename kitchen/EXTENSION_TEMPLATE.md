# Kitchen Extension Template

## How to Extend Kitchen

- Create a new Recipe notebook in `kitchen/notebooks/`.
- Add custom widgets in `kitchen/widgets/`.
- Add utility scripts in `kitchen/scripts/`.

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
