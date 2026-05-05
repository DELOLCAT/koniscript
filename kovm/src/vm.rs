use crate::runtime::{
    Env, ErrCode, Export, KoniFunc, Module, RuntimeType, Value, VmError, VmPanic,
};
use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

#[derive(Clone, Debug)]
pub struct Source {
    pub fp: String,
    pub content: Vec<String>,
}

fn into_int(val: &str) -> Result<i64, VmError> {
    // TODO: Use this for more readable code
    match val.parse::<i64>() {
        Ok(v) => Ok(v),
        Err(_) => Err(VmError {
            msg: "Invalid bytecode".to_string(),
            errcode: ErrCode::InvalidBytecode,
        }),
    }
}

fn into_usize(val: &str) -> Result<usize, VmError> {
    match val.parse::<usize>() {
        Ok(v) => Ok(v),
        Err(_) => Err(VmError {
            msg: "Invalid bytecode".to_string(),
            errcode: ErrCode::InvalidBytecode,
        }),
    }
}
fn get_op(operators: &Vec<String>, idx: usize, name: &str) -> Result<String, VmError> {
    match operators.get(idx) {
        Some(v) => Ok(v.to_string()),
        None => Err(VmError {
            msg: format!("Expected an argument at {idx} for {name}"),
            errcode: ErrCode::ValueError,
        }),
    }
}
fn get_op_int(operators: &Vec<String>, idx: usize, name: &str) -> Result<i64, VmError> {
    return into_int(&get_op(operators, idx, name)?);
}
fn get_op_usize(operators: &Vec<String>, idx: usize, name: &str) -> Result<usize, VmError> {
    return into_usize(&get_op(operators, idx, name)?);
}

fn eval_string(input: &str) -> Result<Value, VmPanic> {
    let mut iter = input.chars().peekable();

    // Parse tag (digits)
    let mut tag = String::new();
    while let Some(&c) = iter.peek() {
        if c.is_ascii_digit() {
            tag.push(c);
            iter.next();
        } else if c == ';' {
            iter.next();
            break;
        } else {
            return Err(VmPanic::UnexpectedValue);
        }
    }

    let mut output = String::new();
    let mut peek = false;
    let mut broken = false;
    for c in iter {
        if peek {
            if c == 'n' {
                output.push('\n');
            } else {
                output.push(c)
            }
            peek = false;
            continue;
        }
        if c == '\\' {
            peek = true;
            continue;
        }
        if c == ';' {
            broken = true;
            break;
        }
        output.push(c);
    }
    if !broken {
        return Err(VmPanic::InvalidBytecode);
    }

    match tag.parse::<i8>() {
        Ok(v) => match Value::new(v, output.as_str()) {
            Ok(v) => Ok(v),
            Err(_) => Err(VmPanic::TagConversionFailed),
        },
        Err(_) => Err(VmPanic::TagConversionFailed),
    }
}

#[derive(Clone)]
pub struct VM {
    pub ins: Vec<Vec<String>>,
    pub global_env: Vec<Value>,
    pub const_pool: Vec<Value>,
    pub lines: Option<Vec<i64>>,
    pub frames: Vec<Frame>,
    pub sources: Vec<Source>,
    pub source_select: Vec<usize>,
    pub mod_stack: Vec<String>,
}
#[derive(Debug, Clone)]
pub struct Frame {
    pub env: Rc<RefCell<Env>>,
    pub ret_addr: Option<usize>,
    pub stack: Vec<Value>,
    pub name: String,
    pub i: usize,
}
impl Frame {
    fn new() -> Self {
        Frame {
            env: Rc::new(RefCell::new(Env {
                parent: None,
                values: vec![],
                exports: HashMap::new(),
            })),
            ret_addr: None,
            stack: vec![],
            name: "[main]".to_string(),
            i: 0,
        }
    }
    fn ret_addr(mut self, ret_addr: usize) -> Self {
        self.ret_addr = Some(ret_addr);
        self
    }
    fn env(mut self, env: Env) -> Self {
        self.env = Rc::new(RefCell::new(env));
        self
    }
    fn name(mut self, name: String) -> Self {
        self.name = name;
        self
    }
}
pub enum FncExit {
    Exit(i32),
    Returned(Value),
}

pub enum StepReturn {
    Exited(i32),
    None,
    Returned(Value),
}

impl VM {
    pub fn new(instructions: Vec<String>) -> Result<Self, VmError> {
        let mut const_table: Vec<Value> = vec![];
        let mut i = 0;
        let mut broken: Option<usize> = None;
        let mut mode = "none";
        let mut local_count = None;
        while i < instructions.len() {
            let line = &instructions[i];

            if line == ".const" {
                mode = "const";
                i += 1;
                continue;
            }
            if line.starts_with(".reqs") {
                for item in line.split(" ") {
                    if item == ".reqs" {
                        continue;
                    }
                    if !crate::runtime::SUPPORTED_FEATURES.contains(&item.to_string()) {
                        return Err(VmError {
                            msg: format!("This VM doesn't support `{}`", item),
                            errcode: ErrCode::CompatibilityError,
                        });
                    }
                }
                i += 1;
                continue;
            }

            if line == ".code" {
                broken = Some(i + 1);
                break;
            }

            if line.starts_with(".frame ") {
                let val = line.split_whitespace().nth(1).ok_or(VmError {
                    msg: "Expected .frame to be followed by an integer".to_string(),
                    errcode: ErrCode::InvalidBytecode,
                })?;

                local_count = Some(val.parse::<i64>().map_err(|_| VmError {
                    msg: "Expected .frame to be preceded by an integer".to_string(),
                    errcode: ErrCode::InvalidBytecode,
                })?);

                i += 1;
                continue;
            }

            if mode == "const" {
                match eval_string(line) {
                    Ok(v) => const_table.push(v),
                    Err(v) => {
                        return Err(VmError {
                            msg: format!("Could not decode string {} in bytecode: {:?}.", line, v),
                            errcode: ErrCode::InvalidBytecode,
                        });
                    }
                }
            }

            i += 1;
        }

        if local_count.is_none() {
            return Err(VmError {
                msg: "The specified program has no local count".to_string(),
                errcode: ErrCode::ValueError,
            });
        }

        if broken.is_none() {
            return Err(VmError {
                msg: "The specified program has no code".to_string(),
                errcode: ErrCode::NoCode,
            });
        }
        let broken = broken.unwrap();
        let mut i = 0;
        let mut sup_lines: Option<usize> = None;
        let mut lines: Vec<i64> = vec![];
        let mut mode = "discover";
        let mut sources: Vec<Source> = Vec::new();
        let mut source_select: Vec<usize> = vec![];
        while i < instructions.len() {
            let line = instructions[i].trim().split(" ").collect::<Vec<&str>>();

            if line.get(0).is_some() && line[0] == ".line" {
                mode = "line";
                sup_lines = match i.try_into() {
                    Ok(v) => v,
                    Err(_) => {
                        return Err(VmError {
                            msg: "Line conversion failed".to_string(),
                            errcode: ErrCode::ConversionFailed,
                        });
                    }
                };
                i += 1;
                continue;
            } else if line.get(0).is_some() && line[0] == ".source" {
                let end = match line.get(1) {
                    Some(v) => v,
                    None => {
                        return Err(VmError {
                            msg: "Expected `.source` to be followed by an integer".to_string(),
                            errcode: ErrCode::InvalidBytecode,
                        });
                    }
                }
                .parse::<usize>();
                let end = match end {
                    Ok(v) => v,
                    Err(_) => {
                        return Err(VmError {
                            msg: "Expected `.source` to be followed by an integer".to_string(),
                            errcode: ErrCode::InvalidBytecode,
                        });
                    }
                };
                let fp = match line.get(2..) {
                    Some(v) => v,
                    None => {
                        return Err(VmError {
                            msg: "Expected `.source` to contain a string".to_string(),
                            errcode: ErrCode::InvalidBytecode,
                        });
                    }
                }
                .join(" ");
                let mut source: Vec<String> = Vec::new();
                i += 1;
                while i < end && i < instructions.len() {
                    source.push(instructions[i].clone());
                    i += 1
                }
                sources.push(Source {
                    fp,
                    content: source,
                });
                continue;
            } else if line.get(0).is_some() && line[0] == ".source_select" {
                mode = "";
                i += 1;
                while i < instructions.len() {
                    let parsed = match instructions[i].parse::<usize>() {
                        Ok(v) => v,
                        Err(_) => {
                            break;
                        }
                    };
                    source_select.push(parsed);
                    i += 1;
                }
                continue;
            }
            if mode == "line" {
                match line[0].parse::<i64>() {
                    Ok(n) => lines.push(n),
                    Err(_) => {
                        return Err(VmError {
                            msg: "Non integer tag in bytecode".to_string(),
                            errcode: ErrCode::InvalidBytecode,
                        });
                    }
                }
            }
            i += 1;
        }
        let frame = Frame::new().env(Env {
            values: vec![None; local_count.unwrap() as usize],
            parent: None,
            exports: HashMap::new(),
        });

        let content = if let Some(x) = sup_lines {
            &instructions[broken..x]
        } else {
            &instructions[broken..]
        };

        let mut ins: Vec<Vec<String>> = vec![];
        for inst in content {
            let mut out: Vec<String> = vec![];
            for idx in inst.split(" ") {
                out.push(idx.to_string())
            }
            ins.push(out)
        }

        Ok(Self {
            ins,
            global_env: crate::runtime::vmenv(),
            const_pool: const_table,
            lines: if sup_lines.is_some() {
                Some(lines)
            } else {
                None
            },
            frames: vec![frame],
            sources,
            source_select,
            mod_stack: vec!["[main]".to_string()],
        })
    }
    //fn global_env(mut self, env: &[Value]) -> Self {
    //    self.global_env = env.to_vec();
    //    self
    //}
    pub fn validate(self) -> Option<VmError> {
        for (i, ins) in self.ins.iter().enumerate() {
            for idx in &ins[1..] {
                if idx.parse::<i64>().is_err() {
                    return Some(VmError {
                        msg: format!(
                            "Invalid bytecode at instruction {}: expected integer, got {}",
                            i, idx
                        ),
                        errcode: crate::runtime::ErrCode::InvalidBytecode,
                    });
                }
            }
        }
        None
    }
    fn get_i(&self) -> usize {
        self.frames.last().unwrap().i
    }
    fn push_to_stack(&mut self, item: Value) {
        self.frames.last_mut().unwrap().stack.push(item);
    }
    pub fn run_function(&mut self, fnc: Value, args: Vec<Value>) -> Result<FncExit, VmError> {
        let arg_count = args.len();
        let func = match fnc {
            Value::Func(f) => f,
            _ => {
                return Err(VmError {
                    msg: format!("Expected a function, got a {}", fnc.display()),
                    errcode: ErrCode::TypeError,
                });
            }
        };
        match &*func {
            KoniFunc::Builtin { name: _, func } => {
                let dereferenced_args: Vec<Value> = args.iter().map(|arg| arg.clone()).collect();
                match func(self, dereferenced_args.as_slice()) {
                    Ok(v) => match v {
                        Value::CallRequest(rec_func, args) => {
                            return self.run_function(
                                Value::Func(Rc::new(rec_func.as_ref().clone())),
                                args.to_vec(),
                            );
                        }
                        _ => self.frames.last_mut().unwrap().stack.push(v),
                    },
                    Err(v) => match v.errcode {
                        ErrCode::ExitSignal(c) => return Ok(FncExit::Exit(c)),
                        _ => return Err(v),
                    },
                }
                Ok(FncExit::Returned(
                    self.frames.last().unwrap().stack.last().unwrap().clone(),
                ))
            }
            KoniFunc::User {
                entry,
                local_count,
                param_count,
                closure,
                name,
                module,
            } => {
                self.mod_stack.push(module.to_string());
                let mut fenv = Env {
                    values: vec![None; *local_count],
                    parent: Some(closure.clone()),
                    exports: HashMap::new(),
                };
                let mut rust_args: Vec<Option<Value>> = vec![];
                for arg in args {
                    rust_args.push(Some(arg))
                }
                if *param_count != arg_count {
                    return Err(VmError {
                        msg: format!("Expected {} args, got {}", param_count, arg_count),
                        errcode: ErrCode::InvalidArgCount,
                    });
                }
                for i in 0..*param_count {
                    fenv.values[i] = rust_args[i].clone()
                }
                let fframe = Frame::new()
                    .env(fenv)
                    .ret_addr(self.frames.last().unwrap().i)
                    .name(name.clone());
                self.frames.push(fframe);
                self.frames.last_mut().unwrap().i = *entry;
                let stack_len = self.frames.len();
                let returned: Value;
                loop {
                    match self.step()? {
                        StepReturn::Exited(v) => return Ok(FncExit::Exit(v)),
                        StepReturn::None => {}
                        StepReturn::Returned(v) => {
                            if self.frames.len() == stack_len {
                                returned = v;
                                break;
                            }
                        }
                    }
                }
                return Ok(FncExit::Returned(returned));
            }
            KoniFunc::BuiltinMethod { name: _, func } => {
                let itm = match self.frames.last_mut().unwrap().stack.pop() {
                    Some(v) => v,
                    None => {
                        return Err(VmError {
                            msg: "StackUnderflow".to_string(),
                            errcode: ErrCode::StackUnderflow,
                        });
                    }
                };
                let result = func(itm, args.as_slice(), self)?;
                self.frames.last_mut().unwrap().stack.push(result);
                return Ok(FncExit::Returned(
                    self.frames.last().unwrap().stack.last().unwrap().clone(),
                ));
            }
        }
    }

    fn pop_from_stack(&mut self) -> Result<Value, VmError> {
        match self.frames.last_mut().unwrap().stack.pop() {
            Some(v) => Ok(v),
            None => Err(VmError {
                msg: "Stack underflow".to_string(),
                errcode: ErrCode::StackUnderflow,
            }),
        }
    }
    pub fn step(&mut self) -> Result<StepReturn, VmError> {
        if self.get_i() > self.ins.len() {
            panic!("Invalid i")
        }
        let operators = &self.ins[self.get_i()];
        let mut returned = false;
        match operators[0].as_str() {
            "JMP" => {
                self.frames.last_mut().unwrap().i = operators[1].parse().expect("Invalid byecode.");
                return Ok(StepReturn::None);
            }
            "JMPIF" => {
                let jump_target_str = operators[1].clone();
                let condv = &mut self.frames.last_mut().unwrap().stack.pop();
                let condv = match condv {
                    Some(v) => v,
                    None => {
                        return Err(VmError {
                            msg: "Stack underflow".to_string(),
                            errcode: ErrCode::StackUnderflow,
                        });
                    }
                };

                let cond = match condv {
                    Value::Bool(v) => v,
                    _ => {
                        return Err(VmError {
                            msg: format!(
                                "Type error: expected a boolean but got a {}",
                                condv.display()
                            ),
                            errcode: ErrCode::TypeError,
                        });
                    }
                };
                if *cond {
                    self.frames.last_mut().unwrap().i =
                        jump_target_str.parse().expect("Invalid byecode.");
                    return Ok(StepReturn::None);
                }
            }
            "JMPIFF" => {
                let jump_target_str = operators[1].clone();
                let condv = self.frames.last_mut().unwrap().stack.pop();
                let condv = match condv {
                    Some(v) => v,
                    None => {
                        return Err(VmError {
                            msg: "Stack underflow".to_string(),
                            errcode: ErrCode::StackUnderflow,
                        });
                    }
                };

                let cond = match condv {
                    Value::Bool(v) => v,
                    _ => {
                        return Err(VmError {
                            msg: format!(
                                "Type error: expected a boolean but got a {}",
                                condv.display()
                            ),
                            errcode: ErrCode::TypeError,
                        });
                    }
                };
                if !cond {
                    self.frames.last_mut().unwrap().i =
                        jump_target_str.parse().expect("Invalid byecode.");
                    return Ok(StepReturn::None);
                }
            }
            "BUILD_ARRAY" => {
                let ops = get_op_usize(operators, 1, &"BUILD_ARRAY")?;
                let mut items: Vec<Value> = Vec::new();
                for _ in 0..ops {
                    match self.frames.last_mut().unwrap().stack.pop() {
                        Some(v) => items.push(v),
                        None => {
                            return Err(VmError {
                                msg: "Stack underflow".to_string(),
                                errcode: ErrCode::StackUnderflow,
                            });
                        }
                    }
                }
                self.push_to_stack(Value::Array(Rc::new(RefCell::new(items))));
            }
            "BUILD_DICT" => {
                let ops = get_op_int(operators, 1, &"BUILD_DICT")?;
                let mut map: Vec<(Value, Value)> = vec![];

                for _ in 0..ops {
                    let k = match self.frames.last_mut().unwrap().stack.pop() {
                        Some(v) => v,
                        None => {
                            return Err(VmError {
                                msg: "Stack Underflow".to_string(),
                                errcode: ErrCode::StackUnderflow,
                            });
                        }
                    };
                    let v = match self.frames.last_mut().unwrap().stack.pop() {
                        Some(v) => v,
                        None => {
                            return Err(VmError {
                                msg: "Stack Underflow".to_string(),
                                errcode: ErrCode::StackUnderflow,
                            });
                        }
                    };
                    map.push((k, v));
                }
                self.push_to_stack(Value::Dict(Rc::new(map)));
            }
            "PUSH_CONST" => {
                let item: Value = self.const_pool[operators[1].parse::<usize>().unwrap()].clone();
                self.push_to_stack(item);
            }
            "PUSH_BUILTIN" => {
                let item: Value = self.global_env[operators[1].parse::<usize>().unwrap()].clone();
                let to_push = match item {
                    Value::RuntimeValue(t) => match t {
                        RuntimeType::Name => Value::String(Rc::new(
                            self.mod_stack
                                .last()
                                .expect("Module stack underflow")
                                .to_string(),
                        )),
                    },
                    _ => item,
                };
                self.push_to_stack(to_push);
            }
            "BREAK" => {
                println!("Breakpoint: at {}:", self.frames.last().unwrap().name);
                println!("Stack : {:#?}", self.frames.last().unwrap().stack);
                let mut b = String::new();
                print!("Press enter to continue");
                let _ = std::io::stdin().read_line(&mut b);
            }
            "GETATTR" => {
                let attrand_unparsed: usize = operators[1].parse().expect("Invalid bytecode");

                let attrand = match self.const_pool.get(attrand_unparsed).cloned() {
                    Some(v) => &v.clone(),
                    None => {
                        return Err(VmError {
                            msg: format!(
                                "Cannot find a value from the constant pool at index {}",
                                attrand_unparsed
                            ),
                            errcode: ErrCode::InvalidBytecode,
                        });
                    }
                };

                let attrand = match attrand {
                    Value::String(v) => v,
                    _ => {
                        return Err(VmError {
                            msg: format!(
                                "Expected attrand for GET_ATTR to be a string, found a {}",
                                attrand.display()
                            ),
                            errcode: ErrCode::InvalidBytecode,
                        });
                    }
                };
                let attrl = match self.frames.last_mut().unwrap().stack.pop() {
                    Some(v) => v,
                    None => {
                        return Err(VmError {
                            msg: "Stack underflow".to_string(),
                            errcode: ErrCode::StackUnderflow,
                        });
                    }
                };
                let out = match attrl {
                    Value::Module(m) => match m.exports.get(&attrand.to_string()) {
                        Some(v) => v.clone().val,
                        None => {
                            return Err(VmError {
                                msg: format!(
                                    "Could not find export {}, did you mark that value as public (export func/var)?",
                                    attrand
                                ),
                                errcode: ErrCode::AttributeError,
                            });
                        }
                    },
                    Value::Dict(_) => {
                        match attrl.dict_get(&Value::String(Rc::new(attrand.to_string()))) {
                            Ok(v) => match v {
                                Some(vs) => vs,
                                None => {
                                    return Err(VmError {
                                        msg: format!(
                                            "Could not find an entry {} from the dict.",
                                            attrand
                                        ),
                                        errcode: ErrCode::AttributeError,
                                    });
                                }
                            },
                            Err(_) => unreachable!(),
                        }
                    }
                    _ => {
                        if let Some(methods) = crate::runtime::ATTRMAP.get(&attrl.get_tag()) {
                            self.frames.last_mut().unwrap().stack.push(attrl.clone());

                            if let Some(v) = methods.get(&attrand.to_string()) {
                                Value::Func(Rc::new(KoniFunc::BuiltinMethod {
                                    name: attrand.to_string(),
                                    func: *v,
                                }))
                            } else {
                                return Err(VmError {
                                    msg: format!(
                                        "No attribute `{}` for type {}",
                                        attrand,
                                        attrl.display()
                                    ),
                                    errcode: ErrCode::AttributeError,
                                });
                            }
                        } else {
                            return Err(VmError {
                                msg: format!(
                                    "Cannot get an attribute from a type of {}",
                                    attrl.display()
                                ),
                                errcode: ErrCode::AttributeError,
                            });
                        }
                    }
                };
                self.frames.last_mut().unwrap().stack.push(out);
            }
            "GET_ITEM" => {
                let item = self.pop_from_stack()?;
                let rhs = self.pop_from_stack()?;

                match item {
                    Value::Array(arr) => {
                        let idx = match rhs {
                            Value::Integer(v) => {
                                if v < 0 {
                                    let abs = v.abs() as usize;
                                    let len = arr.borrow().len();
                                    if abs > len {
                                        return Err(VmError {
                                            msg: format!("Index {} out of bounds", v),
                                            errcode: ErrCode::IndexError,
                                        });
                                    }
                                    len - abs
                                } else {
                                    v as usize
                                }
                            }
                            _ => {
                                return Err(VmError {
                                    msg: format!(
                                        "Cannot index into an array with type `{}`",
                                        rhs.display()
                                    ),
                                    errcode: ErrCode::TypeError,
                                });
                            }
                        };

                        match arr.borrow().get::<usize>(idx as usize) {
                            Some(v) => self.push_to_stack(v.clone()),
                            None => {
                                return Err(VmError {
                                    msg: format!("Index {} out of range", idx),
                                    errcode: ErrCode::IndexError,
                                });
                            }
                        }
                    }
                    Value::Dict(_) => match item.dict_get(&rhs) {
                        Ok(v) => match v {
                            Some(v) => self.push_to_stack(v),
                            None => {
                                return Err(VmError {
                                    msg: format!("Cannot find key {} from dict", rhs.display()),
                                    errcode: ErrCode::IndexError,
                                });
                            }
                        },
                        Err(_) => unreachable!(),
                    },
                    Value::String(s) => {
                        let idx = match rhs {
                            Value::Integer(v) => {
                                if v < 0 {
                                    let abs = v.abs() as usize;
                                    let len = s.len();
                                    if abs > len {
                                        return Err(VmError {
                                            msg: format!("Index {} out of bounds", v),
                                            errcode: ErrCode::IndexError,
                                        });
                                    }
                                    len - abs
                                } else {
                                    v as usize
                                }
                            }
                            _ => {
                                return Err(VmError {
                                    msg: format!(
                                        "Cannot index a string with type `{}`",
                                        rhs.display()
                                    ),
                                    errcode: ErrCode::TypeError,
                                });
                            }
                        };

                        let out = match s.chars().nth(idx as usize) {
                            Some(v) => Value::String(Rc::new(v.to_string())),
                            None => {
                                return Err(VmError {
                                    msg: format!("Index {} out of range", idx),
                                    errcode: ErrCode::IndexError,
                                });
                            }
                        };
                        self.push_to_stack(out);
                    }
                    _ => {
                        return Err(VmError {
                            msg: format!("Cannot get an index from type `{}`", item.display()),
                            errcode: ErrCode::TypeError,
                        });
                    }
                };
            }
            "STORE" => {
                let idx: usize = operators[1].parse().expect("Invalid bytecode");
                let depth: usize = operators[2].parse().expect("Invalid bytecode");

                let mut env_rc = self.frames.last().unwrap().env.clone();

                for _ in 0..depth {
                    let parent = env_rc.borrow().parent.clone().expect("Invalid env chain");
                    env_rc = parent;
                }

                let value = match self.frames.last_mut().unwrap().stack.pop() {
                    Some(v) => v,
                    None => {
                        return Err(VmError {
                            msg: "Stack underflow".to_string(),
                            errcode: ErrCode::StackUnderflow,
                        });
                    }
                };

                let mut env = env_rc.borrow_mut();

                if idx >= env.values.len() {
                    return Err(VmError {
                        msg: format!("Invalid local index {}", idx),
                        errcode: ErrCode::InvalidLocal,
                    });
                }

                env.values[idx] = Some(value);
            }

            "RETRIEVE" => {
                let idx: usize = operators[1].parse().expect("Invalid bytecode");
                let depth: usize = operators[2].parse().expect("Invalid bytecode");
                let mut env_rc = self.frames.last().unwrap().env.clone();

                for _ in 0..depth {
                    let parent = env_rc.borrow().parent.clone().expect("Invalid env chain");
                    env_rc = parent;
                }
                let env = env_rc.borrow_mut();
                match env.values.get(idx) {
                    None => {
                        return Err(VmError {
                            msg: format!("Cannot find a variable at {}:{}", idx, depth),
                            errcode: crate::runtime::ErrCode::VariableNotFound,
                        });
                    }
                    Some(v) => self.push_to_stack(
                        match v {
                            Some(v) => v,
                            None => {
                                return Err(VmError {
                                    msg: format!("The variable at {idx}:{depth} is unallocated."),
                                    errcode: crate::runtime::ErrCode::ValueError,
                                });
                            }
                        }
                        .clone(),
                    ),
                }
            }
            "CALL" => {
                let arg_count: usize = operators[1].parse().expect("Invalid bytecode");
                let mut args: Vec<Value> = Vec::new();
                for _ in 0..arg_count {
                    match self.frames.last_mut().unwrap().stack.pop() {
                        None => {
                            return Err(VmError {
                                msg: "Stack underflow".to_string(),
                                errcode: ErrCode::StackUnderflow,
                            });
                        }
                        Some(v) => args.push(v),
                    }
                }
                args.reverse();
                let func = match self.frames.last_mut().unwrap().stack.pop() {
                    Some(v) => v,
                    None => {
                        return Err(VmError {
                            msg: "Stack underflow".to_string(),
                            errcode: ErrCode::StackUnderflow,
                        });
                    }
                };

                match self.run_function(func, args)? {
                    FncExit::Exit(e) => return Ok(StepReturn::Exited(e)),
                    FncExit::Returned(_) => {}
                }
            }
            "RET" => {
                if self.frames.len() <= 1 {
                    return Err(VmError {
                        msg: "Cannot return in the main frame".to_string(),
                        errcode: ErrCode::InvalidOperation,
                    });
                }
                let to_ret = match self.frames.last_mut().unwrap().stack.pop() {
                    Some(v) => v,
                    None => {
                        return Err(VmError {
                            msg: "Stack underflow".to_string(),
                            errcode: ErrCode::StackUnderflow,
                        });
                    }
                };
                let return_addr: usize = self.frames.last().unwrap().ret_addr.unwrap();
                self.frames.pop();
                self.frames.last_mut().unwrap().i = return_addr;
                self.mod_stack.pop();
                self.push_to_stack(to_ret);
                returned = true;
            }
            "NEG" => {
                let v = match self.frames.last_mut().unwrap().stack.pop() {
                    Some(v) => v,
                    None => {
                        return Err(VmError {
                            msg: "Stack underflow".to_string(),
                            errcode: ErrCode::StackUnderflow,
                        });
                    }
                };
                let out = match v {
                    Value::Integer(val) => Value::Integer(0 - val),
                    _ => {
                        return Err(VmError {
                            msg: format!("Cannot convert a {} to a negative value", v.display()),
                            errcode: ErrCode::TypeError,
                        });
                    }
                };
                self.push_to_stack(out);
            }
            "NOP" => {}
            "POP" => {
                // remove value if present, ignore underflow
                let _ = self.frames.last_mut().unwrap().stack.pop();
            }
            "NOT" => {
                let v = match self.frames.last_mut().unwrap().stack.pop() {
                    Some(v) => v,
                    None => {
                        return Err(VmError {
                            msg: "Stack underflow".to_string(),
                            errcode: ErrCode::StackUnderflow,
                        });
                    }
                };
                let out = match crate::runtime::vm_to_bool_basic(&v, self)? {
                    Value::Bool(b) => Value::Bool(!b),
                    _ => panic!("Extreme VM edge case on NOT"),
                };
                self.push_to_stack(out);
            }
            "ENTER_MODULE" => {
                let mod_name_idx = operators[1].parse::<usize>().expect("Invalid Bytecode");
                let mod_name = match self.const_pool.get(mod_name_idx).cloned() {
                    None => {
                        return Err(VmError {
                            msg: format!(
                                "Could not find a value in the constant pool at index {}",
                                mod_name_idx
                            ),
                            errcode: ErrCode::ValueError,
                        });
                    }
                    Some(v) => match v {
                        Value::String(s) => s,
                        _ => {
                            return Err(VmError {
                                msg: format!(
                                    "Expected ENTER_MODULE to reference a string, not a {}",
                                    v.display()
                                ),
                                errcode: ErrCode::TypeError,
                            });
                        }
                    },
                };
                self.mod_stack.push(mod_name.to_string());
            }
            "MAKE_MODULE" => {
                let mod_name_tmp = self
                    .const_pool
                    .get(operators[1].parse::<usize>().expect("Invalid Bytecode"))
                    .cloned();
                let mod_name = match mod_name_tmp {
                    None => {
                        return Err(VmError {
                            msg: format!(
                                "Could not find a value from the constant pool at index {}",
                                operators[1]
                            ),
                            errcode: ErrCode::ValueError,
                        });
                    }
                    Some(v) => match v {
                        Value::String(s) => s,
                        _ => {
                            return Err(VmError {
                                msg: format!(
                                    "Expected `MAKE_MODULE` to reference a string, not a {}",
                                    v.display()
                                ),
                                errcode: ErrCode::TypeError,
                            });
                        }
                    },
                };
                let new_mod = Module {
                    exports: self.frames.last().unwrap().env.borrow().exports.clone(),
                    name: mod_name.to_string(),
                };
                self.mod_stack.pop();
                self.push_to_stack(Value::Module(Rc::new(new_mod)));
            }

            "EXPORT" => {
                let name = match operators.get(1) {
                    Some(v) => v,
                    None => {
                        return Err(VmError {
                            msg: "Expected EXPORT to have 1 operand, found none".to_string(),
                            errcode: ErrCode::InvalidBytecode,
                        });
                    }
                };
                let name: usize = name.parse().expect("Invalid bytecode");
                let name = match self.const_pool.get(name).cloned() {
                    Some(v) => v,
                    None => {
                        return Err(VmError {
                            msg: format!(
                                "Could not find a value in the constant pool at idx {} for EXPORT",
                                name
                            ),
                            errcode: ErrCode::ValueError,
                        });
                    }
                };
                let name = match name {
                    Value::String(v) => v,
                    _ => {
                        return Err(VmError {
                            msg: format!(
                                "Expected EXPORT to reference to a string, not a {}",
                                name.display()
                            ),
                            errcode: ErrCode::TypeError,
                        });
                    }
                };
                let to_ex = match self.frames.last_mut().unwrap().stack.pop() {
                    Some(v) => v,
                    None => {
                        return Err(VmError {
                            msg: "Stack underflow".to_string(),
                            errcode: ErrCode::StackUnderflow,
                        });
                    }
                };
                self.frames
                    .last_mut()
                    .unwrap()
                    .env
                    .borrow_mut()
                    .exports
                    .insert(
                        name.to_string(),
                        Export {
                            name: match self.mod_stack.last() {
                                Some(v) => v.to_string(),
                                None => {
                                    return Err(VmError {
                                        msg: "Module stack underflow".to_string(),
                                        errcode: ErrCode::StackUnderflow,
                                    });
                                }
                            },
                            val: to_ex,
                        },
                    );
            }
            "MAKE_FUNCTION" => {
                let entry: usize = operators[1].parse().expect("Invalid bytecode");
                let local_count: usize = operators[2].parse().expect("Invalid bytecode");
                let param_count: usize = operators[3].parse().expect("Invalid bytecode");
                let name: usize = operators[4].parse().expect("Invalid bytecode");
                let name = &self.const_pool[name];
                let name = match name {
                    Value::String(v) => v,
                    _ => {
                        return Err(VmError {
                            msg: "Function name should be a string".to_string(),
                            errcode: ErrCode::FuncNameStr,
                        });
                    }
                };
                let closure = self.frames.last().unwrap().env.clone();
                let item = Value::Func(Rc::new(KoniFunc::User {
                    entry,
                    local_count,
                    param_count,
                    closure,
                    name: name.to_string(),
                    module: match self.mod_stack.last() {
                        Some(v) => v.to_string(),
                        None => {
                            return Err(VmError {
                                msg: "Module stack underflow".to_string(),
                                errcode: ErrCode::StackUnderflow,
                            });
                        }
                    },
                }));
                self.push_to_stack(item);
            }
            "REQUIRE" => {
                let mut broken = false;
                for item in 1..operators.len() - 1 {
                    match self.const_pool.get(into_usize(&operators[item])?).cloned() {
                        Some(v) => match v {
                            Value::String(val) => {
                                if !crate::runtime::SUPPORTED_FEATURES.contains(&val) {
                                    broken = true;
                                    break;
                                }
                            }
                            _ => {
                                return Err(VmError {
                                    msg: format!(
                                        "Expected `REQUIRE` to reference to a string, not a {}.",
                                        v.display()
                                    ),
                                    errcode: ErrCode::TypeError,
                                });
                            }
                        },
                        None => {
                            return Err(VmError {
                                msg: format!(
                                    "`REQUIRE` referenced to a constant index that is out of range: {}",
                                    item
                                ),
                                errcode: ErrCode::InvalidBytecode,
                            });
                        }
                    }
                }
                if broken {
                    let jmp_idx = into_usize(operators.last().unwrap())?; // Impossible for `.unwrap()` to panic in this area
                    self.frames.last_mut().unwrap().i = jmp_idx;
                    return Ok(StepReturn::None);
                }
            }
            "DUP" => {
                let to_dup: Value;
                {
                    to_dup = match self.frames.last().unwrap().stack.last() {
                        None => {
                            return Err(VmError {
                                msg: "Stack underflow".to_string(),
                                errcode: ErrCode::StackUnderflow,
                            });
                        }
                        Some(v) => v.clone(),
                    };
                }

                self.frames.last_mut().unwrap().stack.push(to_dup);
            }
            _ => {
                if crate::runtime::funcs().contains_key(&operators[0]) {
                    let op = crate::runtime::funcs().get(&operators[0]).unwrap();
                    let rhs = match self.frames.last_mut().unwrap().stack.pop() {
                        Some(v) => v,
                        None => {
                            return {
                                Err(VmError {
                                    msg: "Stack underflow".to_string(),
                                    errcode: ErrCode::StackUnderflow,
                                })
                            };
                        }
                    };
                    let lhs = match self.frames.last_mut().unwrap().stack.pop() {
                        Some(v) => v,
                        None => {
                            return {
                                Err(VmError {
                                    msg: "Stack underflow".to_string(),
                                    errcode: ErrCode::StackUnderflow,
                                })
                            };
                        }
                    };
                    match op(lhs, rhs, self) {
                        Ok(v) => self.push_to_stack(v),
                        Err(e) => return Err(e),
                    }
                } else {
                    return Err(VmError {
                        msg: format!("Unknown instruction at {}: {}", self.get_i(), operators[0]),
                        errcode: crate::runtime::ErrCode::InvalidBytecode,
                    });
                }
            }
        }
        self.frames.last_mut().unwrap().i += 1;
        if returned {
            Ok(StepReturn::Returned(
                self.frames.last().unwrap().stack.last().unwrap().clone(),
            ))
        } else if !(self.get_i() < self.ins.len()) {
            Ok(StepReturn::Exited(0))
        } else {
            Ok(StepReturn::None)
        }
    }
    pub fn run(&mut self) -> Result<i32, VmError> {
        while self.get_i() < self.ins.len() {
            match self.step()? {
                StepReturn::Exited(v) => return Ok(v),
                StepReturn::None => {}
                StepReturn::Returned(_) => {}
            }
        }
        Ok(0)
    }
}
