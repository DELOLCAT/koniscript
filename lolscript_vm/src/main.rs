use clap::{Parser, Subcommand};
use std::cell::RefCell;
use std::fmt::format;
use std::process::exit;
use std::slice::from_ref;
use std::sync::Condvar;
use std::{fs, slice, vec};
use std::rc::Rc;
use crate::runtime::{Env, Value, VmError, VmPanic};
mod runtime;
use owo_colors::OwoColorize;
use runtime::{ErrCode, LsFunc};

macro_rules! parse_op {
    ($operators:expr, $idx:expr, $typ:ty) => {
        $operators[$idx].parse::<$typ>().expect("Invalid bytecode")
    };
}

#[derive(Parser)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Run {
        file: String,
    },
}
fn eval_string(input: &str) -> Result<Value, VmPanic> {
    let mut iter = input.chars().peekable();

    // Parse tag (digits)
    let mut tag = String::new();
    while let Some(&c) = iter.peek() {
        if c.is_ascii_digit() {
            tag.push(c);
            iter.next();
        } else {
            break;
        }
    }

    // Expect opening quote
    match iter.next() {
        Some('"') => {}
        _ => return Err(VmPanic::StringNeverStarted),
    }

    let mut output = String::new();

    while let Some(c) = iter.next() {
        match c {
            '"' => match tag.parse::<i8>() {
                Ok(v) => return match Value::new(v, output.as_str()) {
                    Ok(v) => Ok(v),
                    Err(_) => return Err(VmPanic::TagConversionFailed)
                },
                Err(_) => return Err(VmPanic::TagConversionFailed)
            },

            '\\' => {
                let esc = iter.next()
                    .ok_or(VmPanic::StringEndedUnexpectedly)?;

                match esc {
                    'n' => output.push('\n'),
                    '"' => output.push('"'),
                    '\\' => output.push('\\'),
                    other => output.push(other),
                }
            }

            other => output.push(other),
        }
    }

    Err(VmPanic::StringNeverEnded)

}

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Run { file } => run(file)
    }
    //runtime::vm_input(std::slice::from_ref(&Value::String("hi".to_string()))).unwrap();
    /*let contents = fs::read_to_string("../test.lsc")
    .expect("Could not read file");
    let contents: Vec<String> = contents.lines().map(String::from).collect();

    let vm = match VM::new(contents) {
        Ok(res) => res,
        Err(e) => {
            println!("{}: {:?}", "Could not setup VM".red().bold(), e);
            exit(1)
        }
    }.debug();*/
    
     
}



struct VM {
    ins: Vec<Vec<String>>,
    i: usize,
    global_env: Vec<Value>,
    const_pool: Vec<Value>,
    builtin_count: i32,
    dbg:bool,
    lines: Option<Vec<i64>>,
    frames: Vec<Frame>
}
#[derive(Debug)]
enum Parent {
    None,
    Some(Box<Env>)
}
struct Frame {
    env: Rc<RefCell<Env>>,
    ret_addr: Option<usize>,
    stack: Vec<Value>
}
impl Frame {
    fn new() -> Self{
        Frame {
            env: Rc::new(RefCell::new(Env {
                parent: None,
                values: vec![]
            })),
            ret_addr: None,
            stack: vec![]
        }
    }
    fn ret_addr(mut self, ret_addr: usize) -> Self {
        self.ret_addr = Some(ret_addr);
        self
    }
    fn env(mut self, env:Env) -> Self {
        self.env = Rc::new(RefCell::new(env));
        self
    }
}

impl VM {
    fn new(instructions:Vec<String>) -> Result<Self, VmPanic> {
        let mut const_table:Vec<Value> = vec![];
        let mut i = 0;
        let mut broken:Option<usize> = None; 
        while i < instructions.len() {
            let line = &instructions[i].trim();
            if *line == ".const" {
                i+=1;
                continue; 
            }
            if *line == ".code" {
                i+=1;
                broken = Some(i);
                break
            }
            match eval_string(line) {
                Ok(v) => {
                    const_table.push(v);
                }
                Err(v) => {
                    return Err(v)
                }
            }
            
            i+=1;
        }
        if broken.is_none() {
            return Err(VmPanic::ConstTableDidntEnd)
        }
        let broken = broken.unwrap();
        let mut i = 0;
        let mut sup_lines:Option<usize> = None;
        let mut lines:Vec<i64> = vec![];
        while i < instructions.len() {
            let line = instructions[i].trim();
            if line == ".line" {
                sup_lines = match Some(i).try_into() {
                    Ok(v) => v,
                    Err(_) => return Err(VmPanic::LineConversionFailed)
                };
                i+=1;
                continue; 
            }
            if sup_lines.is_some() {
                match line.parse::<i64>() {
                    Ok(n) => lines.push(n),
                    Err(_) => return Err(VmPanic::NonIntsInLineTable),
                }
            }
            i+=1;
        }
        
        let frame = Frame::new();  
   
        if let Some(x) = sup_lines {
            let content = &&instructions[broken..x];
            let mut ins:Vec<Vec<String>> = vec![];
            for inst in content.to_vec() {
                let mut out:Vec<String> = vec![];
                for idx in inst.split(" ") {
                    out.push(idx.to_string())
                }
                ins.push(out)
            }
            Ok(Self{i:0, 
                ins: ins, 
                global_env:runtime::vmenv(), 
                const_pool: const_table, 
                builtin_count: runtime::vmenv().len() as i32, 
                dbg: false,
                lines: Some(lines),
                frames: vec![frame]
            })
        } else {
            let mut ins:Vec<Vec<String>> = vec![];
            for inst in instructions.to_vec() {
                let mut out:Vec<String> = vec![];
                for idx in inst.split(" ") {
                    out.push(idx.to_string())
                }
                ins.push(out)
            }
            Ok(Self{i:0, 
                ins: ins, 
                global_env:runtime::vmenv(), 
                const_pool: const_table, 
                builtin_count: runtime::vmenv().len() as i32, 
                dbg: false,
                lines: None,
                frames: vec![frame]
            })
        }
     }
    fn debug(mut self) -> Self{
        self.dbg = true;
        self
    }
    fn global_env(mut self, env:&[Value]) -> Self{
        self.global_env = env.to_vec();
        self.builtin_count = env.len().try_into().unwrap();
        self
    }
    fn validiate(self) -> Option<VmError> {
        for (i, ins) in self.ins.iter().enumerate() {
            for idx in &ins[1..] {
                if idx.parse::<i64>().is_err() {
                    return Some(VmError {
                        msg: format!("Invalid bytecode at instuction {}: expected integer, got {}",
                        i, idx),
                        errcode: runtime::ErrCode::InvalidBytecode })
                }
            }
        }
        None
    }
    fn push_to_stack(&mut self, item: Value) {
        self.frames.last_mut().unwrap().stack.push(item);
    }
    fn pop_from_stack(&mut self) -> Option<Value>{
        self.frames.last_mut().unwrap().stack.pop()
    }
    fn run(mut self) -> Result<Option<Value>, VmError> {
        while self.i < self.ins.len(){
            let operators = &self.ins[self.i];
            match operators[0].as_str() {
                "JMP" => {
                    self.i = operators[1].parse().expect("Invalid byecode.");
                    continue;
                },
                "JMPIF" => {
                    let jump_target_str = operators[1].clone();
                    let condv = self.pop_from_stack();
                    let condv = match condv {
                        Some(v) => v,
                        None => return Err(VmError {
                            msg: "Stack underflow".to_string(),
                            errcode: ErrCode::StackUnderflow,
                        }),
                    };

                    let cond = match condv {
                        Value::Bool(v) => v,
                        _ => return Err(VmError {
                            msg: format!("Type error: expected a boolean but got a {}", condv.display()),
                            errcode: ErrCode::TypeError,
                        }),
                    };
                    if cond {
                        self.i = jump_target_str.parse().expect("Invalid byecode.");
                        continue;
                    }
                },
                "JMPIFF" => {
                    let jump_target_str = operators[1].clone();
                    let condv = self.pop_from_stack();
                    let condv = match condv {
                        Some(v) => v,
                        None => return Err(VmError {
                            msg: "Stack underflow".to_string(),
                            errcode: ErrCode::StackUnderflow,
                        }),
                    };

                    let cond = match condv {
                        Value::Bool(v) => v,
                        _ => return Err(VmError {
                            msg: format!("Type error: expected a boolean but got a {}", condv.display()),
                            errcode: ErrCode::TypeError,
                        }),
                    };
                    if !cond {
                        self.i = jump_target_str.parse().expect("Invalid byecode.");
                        continue;
                    }
                },

                "PUSH_CONST" => {
                    let item: Value = self.const_pool[operators[1].parse::<usize>().unwrap()].clone();
                    self.push_to_stack(item);
                },
                "PUSH_BUILTIN" => {
                    let item:Value = self.global_env[operators[1].parse::<usize>().unwrap()].clone();
                    self.push_to_stack(item);
                },
                "STORE" => {
                    let idx: usize = operators[1].parse().expect("Invalid bytecode");
                    let depth: usize = operators[2].parse().expect("Invalid bytecode");
                    let mut env_rc = self.frames.last().unwrap().env.clone();

                    for _ in 0..depth {
                        let parent = env_rc.borrow().parent.clone().expect("Invalid env chain");
                        env_rc = parent;
                    }
                    {
                        let mut env = env_rc.borrow_mut(); // safe, exclusive mutable borrow

                        // Pop from stack first (does not borrow env)
                        let value = match self.pop_from_stack() {
                            Some(v) => v,
                            None => return Err(VmError {
                                msg: "Stack underflow".to_string(),
                                errcode: ErrCode::StackUnderflow,
                            }),
                        };
                    
                        // Push to environment
                        env.values.push(Some(value));
                    }

                    
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
                        None => {return Err(VmError {msg: format!("Cannot find a variable at {}:{}", idx, depth),
                                                errcode: runtime::ErrCode::VariableNotFound })}
                        Some(v) => self.push_to_stack(v.clone().unwrap()),
                    }
                }
                "CALL" => {
                    let arg_count: usize = operators[1].parse().expect("Invalid bytecode");
                    let mut args:Vec<Value> = Vec::new();
                    for _ in 0..arg_count {
                        match self.pop_from_stack() {
                            None => return Err(VmError { msg: "Stack underflow".to_string(), errcode: ErrCode::StackUnderflow }),
                            Some(v) => args.push(v),
                        }
                    }
                    let func = match self.pop_from_stack() {
                        Some(v) => v,
                        None => return Err(VmError { msg:"Stack underflow".to_string(), errcode: ErrCode::StackUnderflow })
                    };
                    let func = match func {
                        Value::Func(f) => f,
                        _ => return Err(VmError { msg: format!("Expected a function, got a {}", func.display()), errcode: ErrCode::TypeError })
                    };
                    match func {
                        LsFunc::Builtin { name, func } => {
                            match func(&args.as_slice()) {
                                Ok(v) => self.push_to_stack(v),
                                Err(v) => return Err(v)
                            }
                        },
                        LsFunc::User { entry, local_count, param_count, closure,.. } => {
                            let mut fenv = Env{
                                values: vec![None; local_count],
                                parent: Some(closure)
                            };
                            let mut rust_args: Vec<Option<Value>> = vec![];
                            for arg in args {
                                rust_args.push(Some(arg))
                            }
                            for i in 0..param_count {
                                fenv.values[i] = rust_args[i].clone()
                            }
                            let fframe = Frame::new().env(fenv).ret_addr(self.i);
                            self.frames.push(fframe);
                            self.i = entry;
                            continue;
                        }
                    }
                }
                "RET" => {
                    if self.frames.len() <= 1 {
                        match self.pop_from_stack() {
                            Some(v) => return Ok(Some(v)),
                            None => return Err(VmError { msg: "Stack underflow".to_string(), errcode: ErrCode::StackUnderflow })
                        }
                    }
                    let to_ret = match self.pop_from_stack() {
                            Some(v) => v,
                            None => return Err(VmError { msg: "Stack underflow".to_string(), errcode: ErrCode::StackUnderflow })
                        };
                    let return_addr:usize = self.frames.last().unwrap().ret_addr.unwrap();
                    self.i = return_addr;
                    self.frames.pop();
                    self.push_to_stack(to_ret);
                }
                "NOP" => {
                    
                }
                "MAKE_FUNCTION" => {
                    let entry: usize = operators[1].parse().expect("Invalid bytecode");
                    let local_count:usize = operators[2].parse().expect("Invalid bytecode");
                    let param_count:usize = operators[3].parse().expect("Invalid bytecode");
                    let closure = &self.frames.last().unwrap().env;
                    let item = Value::Func(LsFunc::User {
                        entry,
                        local_count,
                        param_count,
                        closure: closure.clone(),
                        name: "todo".to_string()
                    });
                    self.push_to_stack(item);
                }
                _ => {
                    if runtime::funcs().contains_key(&operators[0]) {
                        let op = runtime::funcs().get(&operators[0]).unwrap();
                        let lhs = match self.pop_from_stack() {
                            Some(v) => v,
                            None => return {
                                Err(VmError{
                                    msg:"Stack underflow".to_string(),
                                    errcode: ErrCode::StackUnderflow
                                })
                            }
                        };
                        let rhs = match self.pop_from_stack() {
                            Some(v) => v,
                            None => return {
                                Err(VmError{
                                    msg:"Stack underflow".to_string(),
                                    errcode: ErrCode::StackUnderflow
                                })
                            }
                        };
                        match op(lhs, rhs) {
                            Ok(v) => self.push_to_stack(v),
                            Err(e) => return Err(e)
                        }
                    } else {
                        return Err(VmError {
                            msg: format!("Unknown instruction at {}: {}", self.i, operators[0]),
                            errcode: runtime::ErrCode::InvalidBytecode
                        })
                    }
                }
            }
            self.i+=1
        }
        Ok(None)
}
}

fn run(file: String) {
    println!("{}", file);
    let contents = fs::read_to_string(file)
    .expect("Could not read file");
    let contents: Vec<String> =
        contents.lines().map(|s| s.to_string()).collect();
    let vm = VM::new(contents).unwrap();
    vm.run().unwrap();
}













