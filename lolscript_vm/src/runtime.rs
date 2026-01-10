use std::collections::HashMap;
use std::io::{self, Write};
use std::rc::Rc;
use std::thread::sleep;
use std::cell::RefCell;
use once_cell::sync::Lazy;
#[derive(Debug, Clone)]
pub struct Env {
    pub values:Vec<Option<Value>>,
    pub parent: Option<Rc<RefCell<Env>>>
}
#[derive(Debug)]
pub struct VmError {
    pub msg:String,
    pub errcode: ErrCode
}
#[derive(Debug)]
pub enum VmPanic {
    ConstTableDidntEnd,
    StringNeverStarted,
    StringEndedUnexpectedly,
    StringNeverEnded,
    NonIntsInLineTable,
    TagConversionFailed,
    LineConversionFailed
}
#[repr(i8)]
#[derive(Debug, Copy, Clone)]
pub enum ValueTag {
    Integer = 1,
    String = 2,
    Bool = 3,
    Func = 4,
    Null = 6
}
impl TryFrom<i8> for ValueTag {
    type Error = VmError;

    fn try_from(tag: i8) -> Result<Self, VmError> {
        match tag {
            1 => Ok(ValueTag::Integer),
            2 => Ok(ValueTag::String),
            3 => Ok(ValueTag::Bool),
            4 => Ok(ValueTag::Func),
            6 => Ok(ValueTag::Null),
            _ => Err(VmError {
                msg: format!("Invalid value tag {}", tag),
                errcode: ErrCode::InvalidBytecode,
            }),
        }
    }
}


#[derive(Debug, Clone)]
pub enum Value {
    Integer(i64),
    String(String),
    Bool(bool),
    Func(LsFunc),
    Null
}

impl Value {
    pub fn tag(&self) -> i8{
        match self {
            Value::Integer(_) => ValueTag::Integer as i8,
            Value::String(_) => ValueTag::String as i8,
            Value::Bool(_) => ValueTag::Bool as i8,
            Value::Func(_) => ValueTag::Func as i8,
            Value::Null => ValueTag::Null as i8
        }
    }
    pub fn new(tag:i8, payload:&str) -> Result<Self, VmError>{
        match ValueTag::try_from(tag)? {
            ValueTag::Integer => {
                let out = vm_to_int(std::slice::from_ref(&Value::String(payload.to_string())))?;
                return Ok(out);
            }
            ValueTag::Bool => {
                let out = vm_to_bool(std::slice::from_ref(&Value::String(payload.to_string())))?;
                return  Ok(out);
            }
            ValueTag::Null => {
                return Ok(Value::Null)
            }
            ValueTag::String => {
                return Ok(Value::String(payload.to_string()))
            }
            _ => {
                return Err(VmError {
                    msg: format!("Cannot convert a value with tag {} to an internal value", tag),
                    errcode: ErrCode::ConversionNotPossible })
            }
        }

    }
    pub fn display(&self) -> String {
        match self {
            Value::Integer(_) => "integer".to_string(),
            Value::String(_) => "string".to_string(),
            Value::Bool(_) => "boolean".to_string(),
            Value::Func(f) => {
                match f {
                    LsFunc::User { entry, name,..} => format!("[function {} at {}]", name, entry),
                    LsFunc::Builtin { name,.. } => format!("[builtin function {}]", name)
                }
            },
            Value::Null => "null".to_string()
        }
    }

}
#[derive(Debug, Clone)]
pub enum LsFunc {
    User {
        entry: usize,
        local_count: usize,
        param_count: usize,
        closure: Rc<RefCell<Env>>,
        name:String
    },
    Builtin {
        name: String,
        func: fn(&[Value]) -> Result<Value, VmError>,
    },
}
#[derive(Debug)]
pub enum ErrCode {
    InvalidArgCount = 1,
    ConversionNotPossible = 2,
    ConversionFailed = 3,
    IncorrectType = 4,
    IoError = 5,
    InvalidBytecode = 6,
    VariableNotFound = 7,
    StackUnderflow = 8,
    TypeError = 9,
    InvalidOperandTypes = 10,
    Other = 0
}
pub fn vm_to_str(args: &[Value]) -> Result<Value, VmError> {
    let [item] = args else {
        return Err(VmError {
            msg: format!("Expected 1 argument, got {}", args.len()),
            errcode: ErrCode::InvalidArgCount,
        });
    };
    match item {
        Value::Integer(val) => {
            Result::Ok(Value::String(val.to_string()))
        }
        Value::Bool(val) => {
            if *val {
                Result::Ok(Value::String("true".to_string()))
            } else {
                Result::Ok(Value::String("false".to_string()))
            }
        }
        Value::Func(val) => {
            match val {
                LsFunc::Builtin {name, ..} => {
                    let out = format!("[builtin func {}]", name);
                    Result::Ok(Value::String(out))
                }
                LsFunc::User { entry, name, ..} => {
                    let out = format!("[func {} at ins {}]", name, entry);
                    Result::Ok(Value::String(out))
                }
            }
        }
        Value::String(val) => {
            Result::Ok(Value::String(val.to_string()))
        }
        Value::Null => {
            Result::Ok(Value::String("null".to_string()))
        }
        _ => {
            let out = format!("Cannot convert a {} to a string", item.display());
            Result::Err(VmError { msg: out, errcode: ErrCode::ConversionNotPossible })
        }
    }
    
}
pub fn vm_to_int(args: &[Value]) -> Result<Value, VmError> {
    let [item] = args else {
        return Err(VmError {
            msg: format!("Expected 1 argument, got {}", args.len()),
            errcode: ErrCode::InvalidArgCount,
        });
    };

    match item {
        Value::Integer(v) => Ok(Value::Integer(*v)),
        Value::Bool(v) => Ok(Value::Integer(if *v { 1 } else { 0 })),
        Value::String(v) => {
            v.parse::<i64>()
                .map(Value::Integer)
                .map_err(|_| VmError {
                    msg: format!("Cannot convert \"{}\" to integer", v),
                    errcode: ErrCode::ConversionNotPossible,
                })
        }
        _ => Err(VmError {
            msg: format!("Cannot convert {} to integer", item.display()),
            errcode: ErrCode::ConversionNotPossible,
        }),
    }
}

pub fn vm_to_bool(args: &[Value]) -> Result<Value, VmError> {
    let [item] = args else {
        return Err(VmError {
            msg: format!("Expected 1 argument, got {}", args.len()),
            errcode: ErrCode::InvalidArgCount,
        });
    };

    let b = match item {
        Value::Bool(v) => *v,
        Value::Integer(v) => *v != 0,
        Value::String(v) => !v.is_empty(),
        Value::Null => false,
        _ => {
            return Err(VmError {
                msg: format!("Cannot convert {} to bool", item.display()),
                errcode: ErrCode::ConversionNotPossible,
            });
        }
    };

    Ok(Value::Bool(b))
}
pub fn vm_print(args:&[Value]) -> Result<Value, VmError> {
    let mut rust_args:Vec<String> = Vec::new();
    for item in args {
        let out = vm_to_str(std::slice::from_ref(item));
        match out {
            Ok(val) => {
                if let Value::String(v) = val{
                    rust_args.push(v);
                } else {
                    return Err(VmError { msg: "Could not convert to string".to_string(), errcode: ErrCode::ConversionFailed })
                }
            }
            Err(e) => {
                return Err(e)
            }
        }
        
    }
    
    println!("{}", rust_args.join(" "));
    return Ok(Value::Null);
}
pub fn vm_sleep(args:&[Value]) -> Result<Value, VmError> {
    let [s] = args else {
        return Err(VmError {
            msg: format!("Expected 1 argument, got {}", args.len()),
            errcode: ErrCode::InvalidArgCount 
        });
    };
    match s {
        Value::Integer(secs) => {sleep(std::time::Duration::from_secs(secs.cast_unsigned()))},
        _ => {
            return Err(VmError {
                msg: format!("Expected integer, got {}", s.display()), 
                errcode: ErrCode::IncorrectType 
            })
        }
    }
    return Ok(Value::Null)
}

pub fn vm_input(args: &[Value]) -> Result<Value, VmError> {
    let [_prompt] = args else {
        return Err(VmError {
            msg: format!("Expected 1 argument, got {}", args.len()),
            errcode: ErrCode::InvalidArgCount,
        });
    };

    let prompt = match vm_to_str(args)? {
        Value::String(s) => s,
        _ => unreachable!("vm_to_str must return a string"),
    };

    print!("{}", prompt);
    io::stdout()
        .flush()
        .map_err(|e| VmError {
            msg: format!("Failed to flush stdout: {}", e),
            errcode: ErrCode::IoError,
        })?;

    let mut buf = String::new();
    io::stdin()
        .read_line(&mut buf)
        .map_err(|e| VmError {
            msg: format!("Failed to read line: {}", e),
            errcode: ErrCode::IoError,
        })?;

    if buf.ends_with('\n') {
        buf.pop();
        if buf.ends_with('\r') {
            buf.pop();
        }
    }

    Ok(Value::String(buf))
    
}
pub fn vmenv() -> Vec<Value>{
    vec![
        Value::Func(LsFunc::Builtin { name: "print".to_string(), func: vm_print }),
        Value::Func(LsFunc::Builtin { name: "sleep".to_string(), func: vm_sleep }),
        Value::Func(LsFunc::Builtin { name: "input".to_string(), func: vm_input }),
        Value::Func(LsFunc::Builtin { name: "to_str".to_string(), func: vm_to_str }),
        Value::Func(LsFunc::Builtin { name: "to_int".to_string(), func: vm_to_int }),
        Value::Func(LsFunc::Builtin { name: "to_bool".to_string(), func: vm_to_bool })
    ]
}

fn add(a: Value, b:Value) -> Result<Value, VmError>{
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => {
            Ok(Value::Integer(va + vb))
        }
        (Value::String(va), Value::String(vb)) => {
            let out = format!("{}{}",va, vb);
            Ok(Value::String(out))
        }
        _ => {
            Err(
                VmError {
                    msg: format!("TypeError: Cannot add a {} with a {}", a.display(), b.display()),
                    errcode: ErrCode::TypeError
                }
            )
        }
    }
}
fn sub(a: Value, b:Value) -> Result<Value, VmError>{
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => {
            Ok(Value::Integer(va - vb))
        }
        _ => {
            Err(
                VmError {
                    msg: format!("TypeError: Cannot subtract a {} with a {}", a.display(), b.display()),
                    errcode: ErrCode::TypeError
                }
            )
        }
    }
}

fn div(a: Value, b:Value) -> Result<Value, VmError>{
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => {
            Ok(Value::Integer(va / vb))
        }
        _ => {
            Err(
                VmError {
                    msg: format!("TypeError: Cannot divide a {} with a {}", a.display(), b.display()),
                    errcode: ErrCode::TypeError
                }
            )
        }
    }
}
fn mul(a: Value, b: Value) -> Result<Value, VmError> {
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => {
            Ok(Value::Integer(va * vb))
        }

        (Value::String(s), Value::Integer(n)) => {
            if *n < 0 {
                return Err(VmError {
                    msg: "Type Error: cannot multiply string by negative number".to_string(),
                    errcode: ErrCode::TypeError,
                });
            }

            let mut out = String::new();
            for _ in 0..(*n as usize) {
                out.push_str(s);
            }
            Ok(Value::String(out))
        }

        _ => Err(VmError {
            msg: format!(
                "Type Error: Cannot multiply a {} with a {}",
                a.display(),
                b.display()
            ),
            errcode: ErrCode::TypeError,
        }),
    }
}
fn pow(a: Value, b: Value) -> Result<Value, VmError> {
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => {
            Ok(Value::Integer(va.pow(*vb as u32)))
        }
        _ => Err(VmError {
            msg: format!("TypeError: Cannot raise a {} to a power of a {}", a.display(), b.display()),
            errcode: ErrCode::TypeError,
        }),
    }
}
fn lt(a: Value, b:Value) -> Result<Value, VmError>{
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => {
            Ok(Value::Bool(va < vb))
        }
        (Value::Bool(va), Value::Bool(vb)) => {
            Ok(Value::Bool(va < vb))
        }
        _ => {
            Err(VmError{
                msg: format!("TypeError: Cannot check if a {} is less than a {}", a.display(), b.display()),
                errcode: ErrCode::TypeError
            })
        }
    }
}
fn gt(a: Value, b:Value) -> Result<Value, VmError>{
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => {
            Ok(Value::Bool(va > vb))
        }
        (Value::Bool(va), Value::Bool(vb)) => {
            Ok(Value::Bool(va > vb))
        }
        _ => {
            Err(VmError{
                msg: format!("TypeError: Cannot check if a {} is greater than a {}", a.display(), b.display()),
                errcode: ErrCode::TypeError
            })
        }
    }
}
fn lte(a: Value, b:Value) -> Result<Value, VmError>{
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => {
            Ok(Value::Bool(va <= vb))
        }
        (Value::Bool(va), Value::Bool(vb)) => {
            Ok(Value::Bool(va <= vb))
        }
        _ => {
            Err(VmError{
                msg: format!("TypeError: Cannot check if a {} is less than or equal to a {}", a.display(), b.display()),
                errcode: ErrCode::TypeError
            })
        }
    }
}
fn gte(a: Value, b:Value) -> Result<Value, VmError>{
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => {
            Ok(Value::Bool(va >= vb))
        }
        (Value::Bool(va), Value::Bool(vb)) => {
            Ok(Value::Bool(va >= vb))
        }
        _ => {
            Err(VmError{
                msg: format!("TypeError: Cannot check if a {} is greater than or equal to a {}", a.display(), b.display()),
                errcode: ErrCode::TypeError
            })
        }
    }
}
fn equal_to(a: Value, b:Value) -> Result<Value, VmError>{
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => {
            Ok(Value::Bool(va == vb))
        }
        (Value::Bool(va), Value::Bool(vb)) => {
            Ok(Value::Bool(va == vb))
        }
        _ => {
            Err(VmError{
                msg: format!("TypeError: Cannot check if a {} is equal to a {}", a.display(), b.display()),
                errcode: ErrCode::TypeError
            })
        }
    }
}
fn or(a: Value, b:Value) -> Result<Value, VmError>{
    match (&a, &b) {
        (Value::Bool(va), Value::Bool(vb)) => {
            Ok(Value::Bool(*va || *vb))
        }
        _ => {
            Err(VmError{
                msg: format!("TypeError: OR cannot have types of {} and {}", a.display(), b.display()),
                errcode: ErrCode::TypeError
            })
        }
    }
}
fn and(a: Value, b:Value) -> Result<Value, VmError>{
    match (&a, &b) {
        (Value::Bool(va), Value::Bool(vb)) => {
            Ok(Value::Bool(*va && *vb))
        }
        _ => {
            Err(VmError{
                msg: format!("TypeError: AND cannot have types of {} and {}", a.display(), b.display()),
                errcode: ErrCode::TypeError
            })
        }
    }
}

static FUNCS: Lazy<HashMap<String, fn(Value, Value) -> Result<Value, VmError>>> =
    Lazy::new(||{
    let mut fs: HashMap<String, fn(Value, Value) -> Result<Value, VmError>> = HashMap::new();
    fs.insert("ADD".to_string(), add);
    fs.insert("MUL".to_string(), mul);
    fs.insert("DIV".to_string(), div);
    fs.insert("SUBTRACT".to_string(), sub);
    fs.insert("POW".to_string(), pow);
    fs.insert("LT".to_string(), lt);
    fs.insert("GT".to_string(), gt);
    fs.insert("GTE".to_string(), gte);
    fs.insert("LTE".to_string(), lte);
    fs.insert("EQUAL_TO".to_string(), equal_to);
    fs.insert("OR".to_string(), or);
    fs.insert("AND".to_string(), and);
    fs

});
pub fn funcs() -> &'static HashMap<String, fn(Value, Value) -> Result<Value, VmError>> {
    &FUNCS
}
