from main import Environment, BuiltinFunction
import time

env = Environment()
env.set('print', BuiltinFunction('print', print))
env.set('sleep', BuiltinFunction('sleep', time.sleep))
env.set('input', BuiltinFunction('input', input))
