

def greet(name:str)->str:  # ← スペースがなく black で修正される
    if name is None:  # ← mypy で name は str と明示されてるのに None チェック
        return "Hello"
    else:
        return "Hello " + name

x = greet(123)  # ← mypy: int を渡している（str を期待）

print(x )