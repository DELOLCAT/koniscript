use crate::runtime::{Env, Module, Value, ValueRef, VmError, VmPanic};
use clap::{Parser, Subcommand};
use owo_colors::OwoColorize;
use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;
use std::{fs, vec};
mod runtime;
use runtime::{ErrCode, LsFunc};

#[derive(Parser)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Run { file: String },
    Validate { file: String },
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

    while let Some(c) = iter.next() {
        match c {
            other => output.push(other),
        }
    }
    match tag.parse::<i8>() {
        Ok(v) => match Value::new(v, output.as_str()) {
            Ok(v) => Ok(v),
            Err(_) => Err(VmPanic::TagConversionFailed),
        },
        Err(_) => Err(VmPanic::TagConversionFailed),
    }
}

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Run { file } => run(file),
        Commands::Validate { file } => val(file),
    }
}

fn val(file: String) {
    let contents = fs::read_to_string(file).expect("Could not read file");

    let contents: Vec<String> = contents.lines().map(|s| s.to_string()).collect();
    let vm = VM::new(contents).unwrap();
    match vm.validate() {
        Some(e) => println!("{}", e.msg),
        None => println!("Validation successful"),
    };
}
#[derive(Clone)]
struct VM {
    ins: Vec<Vec<String>>,
    global_env: Vec<Value>,
    const_pool: Vec<Value>,
    lines: Option<Vec<i64>>,
    frames: Vec<Frame>,
    source: Option<Vec<String>>,
}
#[derive(Debug, Clone)]
struct Frame {
    env: Rc<RefCell<Env>>,
    ret_addr: Option<usize>,
    stack: Vec<ValueRef>,
    name: String,
    i: usize,
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

impl VM {
    fn new(instructions: Vec<String>) -> Result<Self, VmError> {
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
                    if !runtime::SUPPORTED_FEATURES.contains(&item.to_string()) {
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
                match eval_string(&line) {
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
        let mut source: Option<Vec<String>> = None;
        let mut mode = "discover";
        while i < instructions.len() {
            let line = instructions[i].trim();
            if line == ".line" {
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
            } else if line == ".source" {
                mode = "source";
                source = Some(Vec::new());
                i += 1;
                continue;
            }
            if mode == "line" {
                match line.parse::<i64>() {
                    Ok(n) => lines.push(n),
                    Err(_) => {
                        return Err(VmError {
                            msg: "Non integer tag in bytecode".to_string(),
                            errcode: ErrCode::InvalidBytecode,
                        });
                    }
                }
            } else if mode == "source" {
                source.as_mut().unwrap().push(instructions[i].clone());
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
            global_env: runtime::vmenv(),
            const_pool: const_table,
            lines: if sup_lines.is_some() {
                Some(lines)
            } else {
                None
            },
            frames: vec![frame],
            source,
        })
    }
    //fn global_env(mut self, env: &[Value]) -> Self {
    //    self.global_env = env.to_vec();
    //    self
    //}
    fn validate(self) -> Option<VmError> {
        for (i, ins) in self.ins.iter().enumerate() {
            for idx in &ins[1..] {
                if idx.parse::<i64>().is_err() {
                    return Some(VmError {
                        msg: format!(
                            "Invalid bytecode at instruction {}: expected integer, got {}",
                            i, idx
                        ),
                        errcode: runtime::ErrCode::InvalidBytecode,
                    });
                }
            }
        }
        None
    }
    fn get_i(&self) -> usize {
        self.frames.last().unwrap().i
    }
    fn push_to_stack(&mut self, item: ValueRef) {
        self.frames.last_mut().unwrap().stack.push(item);
    }

    fn run(&mut self) -> Result<Option<ValueRef>, VmError> {
        while self.get_i() < self.ins.len() {
            let operators = &self.ins[self.get_i()];

            match operators[0].as_str() {
                "JMP" => {
                    self.frames.last_mut().unwrap().i =
                        operators[1].parse().expect("Invalid byecode.");
                    continue;
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

                    let cond = match condv.as_ref() {
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
                        continue;
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

                    let cond = match condv.as_ref() {
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
                        continue;
                    }
                }
                "BUILD_ARRAY" => {
                    let ops = match operators.get(1) {
                        Some(v) => v.parse::<usize>().unwrap(),
                        None => {
                            return Err(VmError {
                                msg: "Expected 1 argument for BUILD_ARRAY".to_string(),
                                errcode: ErrCode::ValueError,
                            });
                        }
                    };
                    let mut items: Vec<ValueRef> = Vec::new();
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
                    self.push_to_stack(Rc::new(Value::Array(Rc::new(RefCell::new(items)))));
                }
                "PUSH_CONST" => {
                    let item: Value =
                        self.const_pool[operators[1].parse::<usize>().unwrap()].clone();
                    self.push_to_stack(Rc::new(item));
                }
                "PUSH_BUILTIN" => {
                    let item: Value =
                        self.global_env[operators[1].parse::<usize>().unwrap()].clone();
                    self.push_to_stack(Rc::new(item));
                }
                "BREAK" => {
                    println!("Breakpoint: at {}:", self.frames.last().unwrap().name);
                    println!("Stack : {:#?}", self.frames.last().unwrap().stack);
                    let mut b = String::new();
                    print!("Press enter to continue");
                    let _ = std::io::stdin().read_line(&mut b);
                }
                "GETATTR" => {
                    let attrand: usize = operators[1].parse().expect("Invalid bytecode");
                    let attrand = match self.const_pool.get(attrand) {
                        Some(v) => v,
                        None => {
                            return Err(VmError {
                                msg: format!(
                                    "Cannot find a value from the constant pool at index {}",
                                    attrand
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
                    let out = match attrl.as_ref() {
                        Value::Module(m) => match m.exports.get(attrand) {
                            Some(v) => v.clone(),
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
                        _ => {
                            if let Some(methods) = runtime::ATTRMAP.get(&attrl.get_tag()) {
                                self.frames.last_mut().unwrap().stack.push(attrl.clone());

                                if let Some(v) = methods.get(attrand) {
                                    Rc::new(Value::Func(LsFunc::BuiltinMethod {
                                        name: attrand.to_string(),
                                        func: *v,
                                    }))
                                } else {
                                    return Err(VmError {
                                        msg: format!("No attribute `{}` for type {}", attrand, attrl.display()),
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

                    // 🔒 Safety check (VERY IMPORTANT)
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
                                errcode: runtime::ErrCode::VariableNotFound,
                            });
                        }
                        Some(v) => self.push_to_stack(
                            match v {
                                Some(v) => v,
                                None => {
                                    return Err(VmError {
                                        msg: format!(
                                            "The variable at {idx}:{depth} is unallocated."
                                        ),
                                        errcode: runtime::ErrCode::ValueError,
                                    });
                                }
                            }
                            .clone(),
                        ),
                    }
                }
                "CALL" => {
                    let arg_count: usize = operators[1].parse().expect("Invalid bytecode");
                    let mut args: Vec<ValueRef> = Vec::new();
                    args.reverse();
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
                    let func = match self.frames.last_mut().unwrap().stack.pop() {
                        Some(v) => v,
                        None => {
                            return Err(VmError {
                                msg: "Stack underflow".to_string(),
                                errcode: ErrCode::StackUnderflow,
                            });
                        }
                    };
                    let func = match func.as_ref() {
                        Value::Func(f) => f,
                        _ => {
                            return Err(VmError {
                                msg: format!("Expected a function, got a {}", func.display()),
                                errcode: ErrCode::TypeError,
                            });
                        }
                    };
                    match func {
                        LsFunc::Builtin { name: _, func } => {
                            let dereferenced_args: Vec<Value> =
                                args.iter().map(|arg| arg.as_ref().clone()).collect();
                            match func(dereferenced_args.as_slice()) {
                                Ok(v) => self.push_to_stack(Rc::new(v)),
                                Err(v) => return Err(v),
                            }
                        }
                        LsFunc::User {
                            entry,
                            local_count,
                            param_count,
                            closure,
                            name,
                        } => {
                            let mut fenv = Env {
                                values: vec![None; *local_count],
                                parent: Some(closure.clone()),
                                exports: HashMap::new(),
                            };
                            let mut rust_args: Vec<Option<ValueRef>> = vec![];
                            for arg in args {
                                rust_args.push(Some(arg))
                            }
                            for i in 0..*param_count {
                                fenv.values[i] = rust_args[i].clone()
                            }
                            let fframe = Frame::new()
                                .env(fenv)
                                .ret_addr(self.get_i())
                                .name(name.clone());
                            self.frames.push(fframe);
                            self.frames.last_mut().unwrap().i = *entry;
                            continue;
                        }
                        LsFunc::BuiltinMethod { name: _, func } => {
                            let itm = match self.frames.last_mut().unwrap().stack.pop() {
                                Some(v) => v,
                                None => {
                                    return Err(VmError {
                                        msg: "StackUnderflow".to_string(),
                                        errcode: ErrCode::StackUnderflow,
                                    });
                                }
                            };
                            let result = func(itm, args.as_slice())?;
                            self.push_to_stack(result);
                        }
                    }
                }
                "RET" => {
                    if self.frames.len() <= 1 {
                        match self.frames.last_mut().unwrap().stack.pop() {
                            Some(v) => return Ok(Some(v)),
                            None => {
                                return Err(VmError {
                                    msg: "Stack underflow".to_string(),
                                    errcode: ErrCode::StackUnderflow,
                                });
                            }
                        }
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
                    self.frames.last_mut().unwrap().i = return_addr;
                    self.frames.pop();
                    self.push_to_stack(to_ret);
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
                    let out = match v.as_ref() {
                        Value::Integer(val) => Rc::new(Value::Integer(0 - val)),
                        _ => {
                            return Err(VmError {
                                msg: format!(
                                    "Cannot convert a {} to a negative value",
                                    v.display()
                                ),
                                errcode: ErrCode::TypeError,
                            });
                        }
                    };
                    self.push_to_stack(out);
                }
                "NOP" => {}
                "MAKE_MODULE" => {
                    let new_mod = Module {
                        exports: self.frames.last().unwrap().env.borrow().exports.clone(),
                        name: None,
                    };
                    self.push_to_stack(Rc::new(Value::Module(new_mod)));
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
                    let name = match self.const_pool.get(name) {
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
                        .insert(name.to_string(), to_ex);
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
                    let item = Rc::new(Value::Func(LsFunc::User {
                        entry,
                        local_count,
                        param_count,
                        closure,
                        name: name.to_string(),
                    }));
                    self.push_to_stack(item);
                }
                "DUP" => {
                    let to_dup: ValueRef;
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
                    if runtime::funcs().contains_key(&operators[0]) {
                        let op = runtime::funcs().get(&operators[0]).unwrap();
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
                        match op(lhs.as_ref().clone(), rhs.as_ref().clone()) {
                            Ok(v) => self.push_to_stack(Rc::new(v)),
                            Err(e) => return Err(e),
                        }
                    } else {
                        return Err(VmError {
                            msg: format!(
                                "Unknown instruction at {}: {}",
                                self.get_i(),
                                operators[0]
                            ),
                            errcode: runtime::ErrCode::InvalidBytecode,
                        });
                    }
                }
            }
            self.frames.last_mut().unwrap().i += 1
        }
        Ok(None)
    }
}

fn run(file: String) {
    let contents = fs::read_to_string(file).expect("Could not read file");
    let contents: Vec<String> = contents.lines().map(|s| s.to_string()).collect();
    let mut vm = match VM::new(contents) {
        Ok(v) => v,
        Err(e) => {
            println!(
                "{}: {}",
                "Error while setting up VM".red(),
                e.msg.red().bold()
            );
            return;
        }
    };
    match vm.run() {
        Ok(opt) => {
            if let Some(v) = opt {
                println!("{:?}", v)
            }
        }
        Err(e) => {
            // Single, clear error line at the top.
            println!("{}: {}\n", e.errcode.to_string().red().bold(), e.msg.red());
            println!("{}", "Traceback (most recent call last):".bold());

            let lines_opt = vm.lines.as_ref();
            let source_opt = vm.source.as_ref();

            for (frame_idx, frame) in vm.frames.iter().rev().enumerate() {
                if frame_idx > 0 {
                    println!()
                } // Add space between frames

                // Frame location info
                let ip_str_val = format!("ins 0x{:04X} ({})", frame.i, frame.i);
                let ip_str = ip_str_val.dimmed();

                if let Some(lines) = lines_opt {
                    if let Some(&line_nr_64) = lines.get(frame.i) {
                        let line_nr = line_nr_64 as usize;
                        println!(
                            "  at {} ({} {})",
                            frame.name.cyan(),
                            "line".green(),
                            (line_nr + 1).to_string().green()
                        );
                        println!("  {}", ip_str);

                        // Code snippet
                        if let Some(source) = source_opt {
                            let radius = 4;
                            let start = line_nr.saturating_sub(radius);
                            let end = std::cmp::min(line_nr + radius + 1, source.len());

                            println!(); // Spacer before code
                            for i in start..end {
                                let line_prefix_val = format!("{:>4} |", i + 1);
                                let line_prefix = line_prefix_val.blue();
                                if i == line_nr {
                                    println!(
                                        "{} {} {}",
                                        "->".red().bold(),
                                        line_prefix,
                                        source[i].bold().underline()
                                    );
                                } else {
                                    println!("   {} {}", line_prefix, &source[i]);
                                }
                            }
                        }
                    } else {
                        println!("  at {} ({})", frame.name.cyan(), ip_str);
                        println!("     (No line information for instruction)");
                    }
                } else {
                    println!("  at {} ({})", frame.name.cyan(), ip_str);
                }
            }
        }
    }
}
