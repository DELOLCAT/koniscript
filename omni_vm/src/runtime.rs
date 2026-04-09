use once_cell::sync::Lazy;
use std::cell::RefCell;
use std::collections::HashMap;
use std::fmt;
use std::io::{self, Write};
use std::rc::Rc;
use std::thread::sleep;

pub type ValueRef = Rc<Value>;
pub type MethodArgs<'a> = &'a [Rc<Value>];
pub type MethodReturn = Result<ValueRef, VmError>;

pub static SUPPORTED_FEATURES: Lazy<Vec<String>> = Lazy::new(|| {
    vec![
        "fs".to_string(),
        "strings.methods".to_string(),
        "types.arrays".to_string(),
        "attributes".to_string(),
        "indexes".to_string(),
        "imports".to_string(),
        "runtime_values".to_string(),
        "types.dicts".to_string(),
    ]
});
#[derive(Debug, Clone, PartialEq)]
pub struct Export {
    pub name: String,
    pub val: ValueRef,
}
#[derive(Debug, Clone)]
pub struct Env {
    pub values: Vec<Option<ValueRef>>,
    pub parent: Option<Rc<RefCell<Env>>>,
    pub exports: HashMap<String, Export>,
}

impl PartialEq for Env {
    fn eq(&self, other: &Self) -> bool {
        self.values == other.values && self.parent == other.parent && self.exports == other.exports
    }
}
#[derive(Debug, Clone, PartialEq)]
pub struct Module {
    pub exports: HashMap<String, Export>,
    pub name: String,
}
#[derive(Debug)]
pub struct VmError {
    pub msg: String,
    pub errcode: ErrCode,
}
impl VmError {
    // TODO: refactor old TypeErrors into this new one
    pub fn make_type_error(expected: &str, received: &Value) -> Self {
        Self {
            msg: format!("Expected `{}`, got `{}`", expected, received.display()),
            errcode: ErrCode::TypeError,
        }
    }
}
#[derive(Debug)]
pub enum VmPanic {
    TagConversionFailed,
    UnexpectedValue,
    InvalidBytecode,
}
#[repr(i8)]
#[derive(Debug, Copy, Clone, PartialEq, Eq, Hash)]
pub enum ValueTag {
    Integer = 1,
    String = 2,
    Bool = 3,
    Func = 4,
    Null = 6,
    Float = 7,
    Module = 8,
    Array = 9,
    RuntimeValue = 10,
    Dict = 11,
    CallRequest = 12,
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
            7 => Ok(ValueTag::Float),
            8 => Ok(ValueTag::Module),
            9 => Ok(ValueTag::Array),
            10 => Ok(ValueTag::RuntimeValue),
            _ => Err(VmError {
                msg: format!("Invalid value tag {}", tag),
                errcode: ErrCode::InvalidBytecode,
            }),
        }
    }
}
#[derive(Debug, Clone)]
pub enum RuntimeType {
    Name,
}
impl RuntimeType {
    fn name(&self) -> String {
        match self {
            RuntimeType::Name => "name".to_string(),
        }
    }
}
#[derive(Debug, Clone)]
pub enum Value {
    Integer(i64),
    String(String),
    Bool(bool),
    Func(OmniFunc),
    Float(f64),
    Module(Module),
    Array(Rc<RefCell<Vec<ValueRef>>>),
    Null,
    RuntimeValue(RuntimeType),
    Dict(Vec<(ValueRef, ValueRef)>),
    CallRequest(Rc<OmniFunc>, Vec<ValueRef>),
}
fn eq_helper(a: &Value, other: &Value) -> Result<bool, ()> {
    match (a, other) {
        (Value::Integer(va), Value::Integer(vb)) => Ok(va == vb),
        (Value::Bool(va), Value::Bool(vb)) => Ok(va == vb),
        (Value::Integer(va), Value::Float(vb)) => Ok(*va as f64 == *vb),
        (Value::Float(va), Value::Integer(vb)) => Ok(*va == *vb as f64),
        (Value::Float(va), Value::Float(vb)) => Ok(va == vb),
        (Value::String(va), Value::String(vb)) => Ok(va == vb),
        (Value::Null, Value::Null) => Ok(true),
        (Value::Null, other) | (other, Value::Null) => Ok(matches!(other, Value::Null)),
        (Value::Array(va), Value::Array(vb)) => {
            if Rc::ptr_eq(va, vb) {
                return Ok(true);
            }
            Ok(*va.borrow() == *vb.borrow())
        }
        _ => Err(()),
    }
}

impl PartialEq for OmniFunc {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (
                OmniFunc::User {
                    name: a,
                    module: ma,
                    ..
                },
                OmniFunc::User {
                    name: b,
                    module: mb,
                    ..
                },
            ) => a == b && ma == mb,
            (OmniFunc::Builtin { name: a, .. }, OmniFunc::Builtin { name: b, .. }) => a == b,
            (OmniFunc::BuiltinMethod { name: a, .. }, OmniFunc::BuiltinMethod { name: b, .. }) => {
                a == b
            }
            _ => false,
        }
    }
}

impl PartialEq for Value {
    fn eq(&self, other: &Self) -> bool {
        match eq_helper(self, other) {
            Ok(v) => v,
            Err(_) => false,
        }
    }
}

impl Value {
    pub fn new(tag: i8, payload: &str) -> Result<Self, VmError> {
        match ValueTag::try_from(tag)? {
            ValueTag::Integer => {
                let out = vm_to_int(std::slice::from_ref(&Value::String(payload.to_string())))?;
                Ok(out)
            }
            ValueTag::Bool => {
                let out = vm_to_bool(std::slice::from_ref(&Value::String(payload.to_string())))?;
                Ok(out)
            }
            ValueTag::Null => Ok(Value::Null),
            ValueTag::String => Ok(Value::String(payload.to_string())),
            ValueTag::Float => {
                let out = vm_to_float(std::slice::from_ref(&Value::String(payload.to_string())))?;
                Ok(out)
            }

            _ => Err(VmError {
                msg: format!(
                    "Cannot convert a value with tag {} to an internal value",
                    tag
                ),
                errcode: ErrCode::ConversionNotPossible,
            }),
        }
    }
    pub fn display(&self) -> String {
        match self {
            Value::Integer(_) => "integer".to_string(),
            Value::String(_) => "string".to_string(),
            Value::Bool(_) => "boolean".to_string(),
            Value::Float(_) => "float".to_string(),
            Value::Func(f) => match f {
                OmniFunc::User { entry, name, .. } => format!("[function {} at {}]", name, entry),
                OmniFunc::Builtin { name, .. } => format!("[builtin function {}]", name),
                OmniFunc::BuiltinMethod { name, .. } => format!("builtin method {}]", name),
            },
            Value::Null => "null".to_string(),
            Value::Module(m) => format!("[module {}]", m.name),
            Value::Array(_) => "array".to_string(),
            Value::RuntimeValue(r) => format!("[runtime value '{}']", r.name()), // This should never be called
            Value::Dict(_) => {
                match self
                    .dict_get(&Value::String("_display_type".to_string()))
                    .unwrap()
                {
                    None => "dict".to_string(),
                    Some(v) => match v.as_ref() {
                        Value::String(s) => s.to_string(),
                        _ => "dict".to_string(),
                    },
                }
            }
            Value::CallRequest(r, _) => {
                format!(
                    "[call request for {}]",
                    Value::Func(r.as_ref().clone()).display()
                )
            } // This should also never be called
        }
    }
    pub fn get_tag(&self) -> ValueTag {
        match self {
            Value::String(_) => ValueTag::String,
            Value::Integer(_) => ValueTag::Integer,
            Value::Array(_) => ValueTag::Array,
            Value::Bool(_) => ValueTag::Bool,
            Value::Float(_) => ValueTag::Float,
            Value::Module(_) => ValueTag::Module,
            Value::Func(_) => ValueTag::Func,
            Value::Null => ValueTag::Null,
            Value::RuntimeValue(_) => ValueTag::RuntimeValue,
            Value::Dict(_) => ValueTag::Dict,
            Value::CallRequest(_, _) => ValueTag::CallRequest,
        }
    }
    pub fn repr(&self) -> String {
        match self {
            Value::String(v) => format!("'{v}'"),
            Value::Integer(v) => v.to_string(),
            Value::Bool(v) => if *v { "true" } else { "false" }.to_string(),
            Value::Float(v) => v.to_string(),
            Value::Func(v) => match v {
                OmniFunc::Builtin { name, .. } => format!("<builtin fn {}>", name),
                OmniFunc::User { entry, name, .. } => format!("<fn {} at {}>", name, entry),
                OmniFunc::BuiltinMethod { name, .. } => format!("<builtin method {}>", name),
            },
            Value::Module(v) => {
                format!("<module {} ({} exports)>", v.name, v.exports.len())
            }
            Value::Null => "null".to_string(),
            Value::Array(items_rc) => {
                let items = items_rc.borrow();
                let mut output = "[".to_string();
                let mut first = true;
                for item in items.iter() {
                    if !first {
                        output.push_str(", ");
                    }
                    output.push_str(&item.repr());
                    first = false;
                }
                output.push(']');
                output
            }
            Value::RuntimeValue(_) => panic!("Illegal value received for repr()"), // It should've been converted on PUSH_BUILTIN
            Value::Dict(_) => match self.dict_get(&Value::String("_repr".to_string())).unwrap() {
                Some(v) => match v.as_ref() {
                    Value::String(v) => v.to_string(),
                    _ => self.dict_display().unwrap(),
                },
                _ => self.dict_display().unwrap()
            },
            Value::CallRequest(_, _) => panic!("Illegal value received for repr()"), // It should've been converted on call
        }
    }
    pub fn dict_get(&self, key: &Value) -> Result<Option<ValueRef>, VmError> {
        match self {
            Value::Dict(d) => Ok(d.iter().find(|(k, _)| **k == *key).map(|(_, v)| v.clone())),
            _ => Err(VmError {
                msg: format!("Expected a dict, got a(n) {}", self.display()),
                errcode: ErrCode::TypeError,
            }),
        }
    }
    pub fn dict_display(&self) -> Result<String, VmError> {
        match self {
            Value::Dict(d) => {
                let mut out = String::new();
                out.push('{');
                for (i, (k, v)) in d.iter().enumerate() {
                    out.push_str(&k.repr());
                    out.push_str(": ");
                    out.push_str(&v.repr());
                    if i != d.len() - 1 {
                        out.push_str(", ")
                    }
                }
                out.push('}');
                return Ok(out);
            }
            _ => Err(VmError {
                msg: format!("Expected a dict, got a(n) {}", self.display()),
                errcode: ErrCode::TypeError,
            }),
        }
    }
}
#[derive(Debug, Clone)]
pub enum OmniFunc {
    User {
        entry: usize,
        local_count: usize,
        param_count: usize,
        closure: Rc<RefCell<Env>>,
        name: String,
        module: String,
    },
    Builtin {
        name: String,
        func: fn(&[Value]) -> Result<Value, VmError>,
    },
    BuiltinMethod {
        name: String,
        func: fn(Rc<Value>, &[Rc<Value>]) -> Result<Rc<Value>, VmError>,
    },
}
#[repr(i32)]
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
    FuncNameStr = 11,
    InvalidLocal = 12,
    CompatibilityError = 13,
    NoCode = 14,
    ValueError = 15,
    AttributeError = 17,
    ExitSignal(i32) = 18,
    InvalidOperation = 19,
    IndexError = 20,
}
impl fmt::Display for ErrCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:?}", self)
    }
}

pub fn vm_to_str(args: &[Value]) -> Result<Value, VmError> {
    let [item] = args else {
        return Err(VmError {
            msg: format!("Expected 1 argument, got {}", args.len()),
            errcode: ErrCode::InvalidArgCount,
        });
    };
    match item {
        Value::Integer(val) => Result::Ok(Value::String(val.to_string())),
        Value::Float(val) => Result::Ok(Value::String(val.to_string())),
        Value::Bool(val) => {
            if *val {
                Result::Ok(Value::String("true".to_string()))
            } else {
                Result::Ok(Value::String("false".to_string()))
            }
        }
        Value::Func(val) => match val {
            OmniFunc::Builtin { name, .. } => {
                let out = format!("[builtin func {}]", name);
                Result::Ok(Value::String(out))
            }
            OmniFunc::User { entry, name, .. } => {
                let out = format!("[func {} at ins {}]", name, entry);
                Result::Ok(Value::String(out))
            }
            OmniFunc::BuiltinMethod { name, .. } => {
                let out = format!("[builtin method {}]", name);
                Ok(Value::String(out))
            }
        },
        Value::String(val) => Result::Ok(Value::String(val.to_string())),
        Value::Null => Result::Ok(Value::String("null".to_string())),
        Value::Array(_) => Ok(Value::String(item.repr())),
        Value::Module(v) => Ok(Value::String(format!(
            "[module {} with {} exports]",
            v.name,
            v.exports.len()
        ))),
        Value::Dict(_) => match item.dict_get(&Value::String("_str".to_string())).unwrap() {
            Some(v) => match v.as_ref() {
                Value::String(v) => Ok(Value::String(v.to_string())),
                _ => Ok(Value::String(item.dict_display()?)),
            },
            _ => Ok(Value::String(item.dict_display()?)),
        },
        _ => todo!("{}", item.display()),
    }
}
pub fn vm_to_float(args: &[Value]) -> Result<Value, VmError> {
    let [item] = args else {
        return Err(VmError {
            msg: format!("Expected 1 argument, got {}", args.len()),
            errcode: ErrCode::InvalidArgCount,
        });
    };
    match item {
        Value::Integer(val) => Result::Ok(Value::Float(*val as f64)),
        Value::Float(val) => Result::Ok(Value::Float(*val)),
        Value::Bool(val) => {
            if *val {
                Result::Ok(Value::Float(1.0))
            } else {
                Result::Ok(Value::Float(0.0))
            }
        }
        Value::String(val) => {
            let v = match val.parse::<f64>() {
                Ok(val) => val,
                Err(_) => {
                    return Err(VmError {
                        msg: format!("Cannot convert the string \"{}\" to a float", val),
                        errcode: ErrCode::TypeError,
                    });
                }
            };
            Result::Ok(Value::Float(v))
        }
        Value::Null => Result::Ok(Value::Float(0.0)),
        _ => {
            let out = format!("Cannot convert a {} to a float", item.display());
            Result::Err(VmError {
                msg: out,
                errcode: ErrCode::ConversionNotPossible,
            })
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
        Value::Float(v) => Ok(Value::Integer(*v as i64)),
        Value::Bool(v) => Ok(Value::Integer(if *v { 1 } else { 0 })),
        Value::String(v) => v.parse::<i64>().map(Value::Integer).map_err(|_| VmError {
            msg: format!("Invalid string for conversion to integer: {}", v),
            errcode: ErrCode::ConversionNotPossible,
        }),
        _ => Err(VmError {
            msg: format!("Cannot convert a {} to an integer", item.display()),
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
        Value::Float(v) => *v != 0.0,
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
pub fn vm_println(args: &[Value]) -> Result<Value, VmError> {
    print_helper(args)?;
    println!();
    Ok(Value::Null)
}
fn print_helper(args: &[Value]) -> Result<(), VmError> {
    let mut rust_args: Vec<String> = Vec::new();
    for item in args {
        let out = vm_to_str(std::slice::from_ref(item));
        match out {
            Ok(val) => {
                if let Value::String(v) = val {
                    rust_args.push(v);
                } else {
                    return Err(VmError {
                        msg: format!("Could not convert to string"),
                        errcode: ErrCode::ConversionFailed,
                    });
                }
            }
            Err(e) => return Err(e),
        }
    }
    print!("{}", rust_args.join(" "));
    Ok(())
}
pub fn vm_print(args: &[Value]) -> Result<Value, VmError> {
    print_helper(args)?;
    io::stdout().flush().map_err(|e| VmError {
        msg: format!("Failed to flush stdout: {}", e),
        errcode: ErrCode::IoError, // Or a specific I/O error code
    })?;

    Ok(Value::Null)
}
pub fn vm_sleep(args: &[Value]) -> Result<Value, VmError> {
    let [s] = args else {
        return Err(VmError {
            msg: format!("Expected 1 argument, got {}", args.len()),
            errcode: ErrCode::InvalidArgCount,
        });
    };
    match s {
        Value::Integer(secs) => sleep(std::time::Duration::from_secs(secs.cast_unsigned())),
        Value::Float(secs) => sleep(std::time::Duration::from_secs_f64(*secs)),
        _ => {
            return Err(VmError {
                msg: format!("Expected integer or float, got {}", s.display()),
                errcode: ErrCode::IncorrectType,
            });
        }
    }
    Ok(Value::Null)
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
    io::stdout().flush().map_err(|e| VmError {
        msg: format!("Failed to flush stdout: {}", e),
        errcode: ErrCode::IoError,
    })?;

    let mut buf = String::new();
    io::stdin().read_line(&mut buf).map_err(|e| VmError {
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
pub fn vm_hi(_args: &[Value]) -> Result<Value, VmError> {
    println!("hi from math");
    Ok(Value::Null)
}
pub fn vmenv() -> Vec<Value> {
    vec![
        Value::Func(OmniFunc::Builtin {
            name: "print".to_string(),
            func: vm_print,
        }),
        Value::Func(OmniFunc::Builtin {
            name: "println".to_string(),
            func: vm_println,
        }),
        Value::Func(OmniFunc::Builtin {
            name: "sleep".to_string(),
            func: vm_sleep,
        }),
        Value::Func(OmniFunc::Builtin {
            name: "input".to_string(),
            func: vm_input,
        }),
        Value::Func(OmniFunc::Builtin {
            name: "to_str".to_string(),
            func: vm_to_str,
        }),
        Value::Func(OmniFunc::Builtin {
            name: "to_int".to_string(),
            func: vm_to_int,
        }),
        Value::Func(OmniFunc::Builtin {
            name: "to_bool".to_string(),
            func: vm_to_bool,
        }),
        Value::Func(OmniFunc::Builtin {
            name: "to_float".to_string(),
            func: vm_to_float,
        }),
        Value::Func(OmniFunc::Builtin {
            name: "exit".to_string(),
            func: vm_exit,
        }),
        Value::Func(OmniFunc::Builtin {
            name: "len".to_string(),
            func: vm_len,
        }),
        Value::Module(Module {
            exports: HashMap::from([(
                "hi".to_string(),
                Export {
                    name: "math".to_string(),
                    val: Rc::new(Value::Func(OmniFunc::Builtin {
                        name: "hi".to_string(),
                        func: vm_hi,
                    })),
                },
            )]),
            name: "math".to_string(),
        }),
        Value::RuntimeValue(RuntimeType::Name),
    ]
}

fn vm_exit(args: &[Value]) -> Result<Value, VmError> {
    if args.len() > 1 {
        return Err(VmError {
            msg: format!("Expected 0 to 1 argument, got {}.", args.len()),
            errcode: ErrCode::InvalidArgCount,
        });
    }
    let item = match args.first() {
        Some(v) => v,
        None => &Value::Integer(0),
    };
    let code = match item {
        Value::Integer(v) => v,
        _ => {
            return Err(VmError::make_type_error("integer", item));
        }
    };
    Err(VmError {
        msg: "".to_string(),
        errcode: ErrCode::ExitSignal(*code as i32),
    })
}

fn vm_len(args: &[Value]) -> Result<Value, VmError> {
    expect_args(args, 1)?;
    match &args[0] {
        Value::String(v) => Ok(Value::Integer(v.len().try_into().unwrap())),
        Value::Array(v) => Ok(Value::Integer(v.borrow().len().try_into().unwrap())),
        Value::Dict(d) => {
            match args[0]
                .dict_get(&Value::String("_len".to_string()))
                .unwrap()
            {
                None => Ok(Value::Integer(d.len().try_into().unwrap())),
                Some(v) => match v.as_ref() {
                    Value::Func(v) => Ok(Value::CallRequest(
                        Rc::new(v.clone()),
                        vec![Rc::new(args[0].clone())],
                    )), // TODO: perhaps find out how to not clone this
                    Value::Integer(v) => Ok(Value::Integer(*v)),
                    _ => Ok(Value::Integer(d.len().try_into().unwrap()))
                    
                },
            }
        }
        _ => Err(VmError {
            msg: format!("Cannot find the `len()` of a {}", args[0].display()),
            errcode: ErrCode::TypeError,
        }),
    }
}
fn add(a: Value, b: Value) -> Result<Value, VmError> {
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => Ok(Value::Integer(va + vb)),
        (Value::Integer(va), Value::Float(vb)) => Ok(Value::Float(*va as f64 + vb)),

        (Value::Float(va), Value::Integer(vb)) => Ok(Value::Float(va + *vb as f64)),
        (Value::Float(va), Value::Float(vb)) => Ok(Value::Float(va + vb)),

        (Value::String(va), Value::String(vb)) => {
            let out = format!("{}{}", va, vb);
            Ok(Value::String(out))
        }
        _ => Err(VmError {
            msg: format!(
                "TypeError: Cannot add a {} with a {}",
                a.display(),
                b.display()
            ),
            errcode: ErrCode::TypeError,
        }),
    }
}
fn sub(a: Value, b: Value) -> Result<Value, VmError> {
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => Ok(Value::Integer(va - vb)),
        (Value::Float(va), Value::Integer(vb)) => Ok(Value::Float(va - *vb as f64)),

        (Value::Integer(va), Value::Float(vb)) => Ok(Value::Float(*va as f64 - vb)),
        (Value::Float(va), Value::Float(vb)) => Ok(Value::Float(va - vb)),

        _ => Err(VmError {
            msg: format!(
                "TypeError: Cannot subtract a {} with a {}",
                a.display(),
                b.display()
            ),
            errcode: ErrCode::TypeError,
        }),
    }
}

fn div(a: Value, b: Value) -> Result<Value, VmError> {
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => Ok(Value::Integer(va / vb)),
        (Value::Float(va), Value::Integer(vb)) => Ok(Value::Float(va / *vb as f64)),

        (Value::Integer(va), Value::Float(vb)) => Ok(Value::Float(*va as f64 / vb)),
        (Value::Float(va), Value::Float(vb)) => Ok(Value::Float(va / vb)),

        _ => Err(VmError {
            msg: format!(
                "TypeError: Cannot divide a {} with a {}",
                a.display(),
                b.display()
            ),
            errcode: ErrCode::TypeError,
        }),
    }
}
fn vm_mod(a: Value, b: Value) -> Result<Value, VmError> {
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => Ok(Value::Integer(va % vb)),
        (Value::Float(va), Value::Integer(vb)) => Ok(Value::Float(va % *vb as f64)),

        (Value::Integer(va), Value::Float(vb)) => Ok(Value::Float(*va as f64 % vb)),
        (Value::Float(va), Value::Float(vb)) => Ok(Value::Float(va % vb)),

        _ => Err(VmError {
            msg: format!(
                "TypeError: Cannot apply modulo a {} with a {}",
                a.display(),
                b.display()
            ),
            errcode: ErrCode::TypeError,
        }),
    }
}
fn mul(a: Value, b: Value) -> Result<Value, VmError> {
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => Ok(Value::Integer(va * vb)),
        (Value::Float(va), Value::Integer(vb)) => Ok(Value::Float(va * *vb as f64)),

        (Value::Integer(va), Value::Float(vb)) => Ok(Value::Float(*va as f64 * vb)),
        (Value::Float(va), Value::Float(vb)) => Ok(Value::Float(va * vb)),

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
        (Value::Integer(va), Value::Integer(vb)) => Ok(Value::Integer(va.pow(*vb as u32))),
        (Value::Integer(va), Value::Float(vb)) => Ok(Value::Integer(va.pow(*vb as u32))),
        (Value::Float(va), Value::Integer(vb)) => Ok(Value::Float(va.powf(*vb as f64))),

        (Value::Float(va), Value::Float(vb)) => Ok(Value::Float(va.powf(*vb))),

        _ => Err(VmError {
            msg: format!(
                "TypeError: Cannot raise a {} to a power of a {}",
                a.display(),
                b.display()
            ),
            errcode: ErrCode::TypeError,
        }),
    }
}
fn lt(a: Value, b: Value) -> Result<Value, VmError> {
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => Ok(Value::Bool(va < vb)),
        (Value::Bool(va), Value::Bool(vb)) => Ok(Value::Bool(va < vb)),
        (Value::Float(va), Value::Integer(vb)) => Ok(Value::Bool(*va < *vb as f64)),
        (Value::Integer(va), Value::Float(vb)) => Ok(Value::Bool((*va as f64) < *vb)),
        (Value::Float(va), Value::Float(vb)) => Ok(Value::Bool(va < vb)),
        _ => Err(VmError {
            msg: format!(
                "TypeError: Cannot check if a {} is less than a {}",
                a.display(),
                b.display()
            ),
            errcode: ErrCode::TypeError,
        }),
    }
}
fn gt(a: Value, b: Value) -> Result<Value, VmError> {
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => Ok(Value::Bool(va > vb)),
        (Value::Bool(va), Value::Bool(vb)) => Ok(Value::Bool(va > vb)),
        (Value::Float(va), Value::Integer(vb)) => Ok(Value::Bool(*va > *vb as f64)),
        (Value::Integer(va), Value::Float(vb)) => Ok(Value::Bool((*va as f64) > *vb)),
        (Value::Float(va), Value::Float(vb)) => Ok(Value::Bool(va > vb)),
        _ => Err(VmError {
            msg: format!(
                "TypeError: Cannot check if a {} is greater than a {}",
                a.display(),
                b.display()
            ),
            errcode: ErrCode::TypeError,
        }),
    }
}
fn lte(a: Value, b: Value) -> Result<Value, VmError> {
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => Ok(Value::Bool(va <= vb)),
        (Value::Bool(va), Value::Bool(vb)) => Ok(Value::Bool(va <= vb)),
        (Value::Float(va), Value::Integer(vb)) => Ok(Value::Bool(*va <= *vb as f64)),
        (Value::Integer(va), Value::Float(vb)) => Ok(Value::Bool((*va as f64) <= *vb)),
        (Value::Float(va), Value::Float(vb)) => Ok(Value::Bool(va <= vb)),
        _ => Err(VmError {
            msg: format!(
                "TypeError: Cannot check if a {} is less than or equal to a {}",
                a.display(),
                b.display()
            ),
            errcode: ErrCode::TypeError,
        }),
    }
}
fn gte(a: Value, b: Value) -> Result<Value, VmError> {
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => Ok(Value::Bool(va >= vb)),
        (Value::Bool(va), Value::Bool(vb)) => Ok(Value::Bool(va >= vb)),
        (Value::Float(va), Value::Integer(vb)) => Ok(Value::Bool(*va >= *vb as f64)),
        (Value::Integer(va), Value::Float(vb)) => Ok(Value::Bool((*va as f64) >= *vb)),
        (Value::Float(va), Value::Float(vb)) => Ok(Value::Bool(va >= vb)),
        _ => Err(VmError {
            msg: format!(
                "TypeError: Cannot check if a {} is greater than or equal to a {}",
                a.display(),
                b.display()
            ),
            errcode: ErrCode::TypeError,
        }),
    }
}

fn equal_to(a: Value, b: Value) -> Result<Value, VmError> {
    match eq_helper(&a, &b) {
        Ok(v) => Ok(Value::Bool(v)),
        Err(_) => Err(VmError {
            msg: format!(
                "TypeError: Cannot check if a {} is equal to a {}",
                a.display(),
                b.display()
            ),
            errcode: ErrCode::TypeError,
        }),
    }
}

fn not_equal_to(a: Value, b: Value) -> Result<Value, VmError> {
    let a_display = a.display();
    let b_display = b.display();
    match equal_to(a, b) {
        Ok(v) => match v {
            Value::Bool(vb) => Ok(Value::Bool(!vb)),
            _ => unreachable!(),
        },
        Err(_) => {
            return Err(VmError {
                msg: format!(
                    "Cannot check if a(n) {} is not equal to a(n) {}",
                    a_display, b_display
                ),
                errcode: ErrCode::TypeError,
            });
        }
    }
}

fn or(a: Value, b: Value) -> Result<Value, VmError> {
    match (&a, &b) {
        (Value::Bool(va), Value::Bool(vb)) => Ok(Value::Bool(*va || *vb)),
        _ => Err(VmError {
            msg: format!(
                "TypeError: OR cannot have types of {} and {}",
                a.display(),
                b.display()
            ),
            errcode: ErrCode::TypeError,
        }),
    }
}
fn and(a: Value, b: Value) -> Result<Value, VmError> {
    match (&a, &b) {
        (Value::Bool(va), Value::Bool(vb)) => Ok(Value::Bool(*va && *vb)),
        _ => Err(VmError {
            msg: format!(
                "TypeError: AND cannot have types of {} and {}",
                a.display(),
                b.display()
            ),
            errcode: ErrCode::TypeError,
        }),
    }
}

static FUNCS: Lazy<HashMap<String, fn(Value, Value) -> Result<Value, VmError>>> = Lazy::new(|| {
    let mut fs: HashMap<String, fn(Value, Value) -> Result<Value, VmError>> = HashMap::new();
    fs.insert("ADD".to_string(), add);
    fs.insert("MUL".to_string(), mul);
    fs.insert("DIV".to_string(), div);
    fs.insert("MOD".to_string(), vm_mod);
    fs.insert("SUB".to_string(), sub);
    fs.insert("POW".to_string(), pow);
    fs.insert("LT".to_string(), lt);
    fs.insert("GT".to_string(), gt);
    fs.insert("GTE".to_string(), gte);
    fs.insert("LTE".to_string(), lte);
    fs.insert("EQ".to_string(), equal_to);
    fs.insert("NEQ".to_string(), not_equal_to);
    fs.insert("OR".to_string(), or);
    fs.insert("AND".to_string(), and);
    fs
});
pub fn funcs() -> &'static HashMap<String, fn(Value, Value) -> Result<Value, VmError>> {
    &FUNCS
}
fn expect_args<T>(args: &[T], n: usize) -> Result<(), VmError> {
    if args.len() != n {
        Err(VmError {
            msg: format!("Expected {} argument(s), got {}", n, args.len()),
            errcode: ErrCode::ValueError,
        })
    } else {
        Ok(())
    }
}
fn arr_pop(item: Rc<Value>, args: &[Rc<Value>]) -> Result<Rc<Value>, VmError> {
    expect_args(args, 0)?;
    match item.as_ref() {
        Value::Array(ar) => match ar.borrow_mut().pop() {
            Some(v) => Ok(v),
            None => Err(VmError {
                msg: "Cannot `pop()` from an empty array".to_string(),
                errcode: ErrCode::InvalidOperation,
            }),
        },
        _ => Err(VmError {
            msg: format!("Expected an array, got a {}", item.display()),
            errcode: ErrCode::TypeError,
        }),
    }
}
fn arr_contains(item: ValueRef, args: &[ValueRef]) -> Result<ValueRef, VmError> {
    expect_args(args, 1)?;
    let cont = &args[0];
    match item.as_ref() {
        Value::Array(arr) => Ok(Rc::new(Value::Bool(arr.borrow().contains(cont)))),
        _ => Err(VmError {
            msg: format!("Expected an array, got a {}", item.display()),
            errcode: ErrCode::TypeError,
        }),
    }
}
fn arr_push(item: Rc<Value>, args: &[Rc<Value>]) -> Result<Rc<Value>, VmError> {
    expect_args(args, 1)?;

    match item.as_ref() {
        Value::Array(ar) => {
            ar.borrow_mut().push(args[0].clone());
            Ok(item.clone())
        }

        other => Err(VmError {
            msg: format!("`push` only works on arrays, not {}", other.display()),
            errcode: ErrCode::TypeError,
        }),
    }
}
pub static ATTRMAP: Lazy<
    HashMap<ValueTag, HashMap<String, fn(Rc<Value>, &[Rc<Value>]) -> Result<Rc<Value>, VmError>>>,
> = Lazy::new(|| {
    let mut attramp = HashMap::new(); // Initialize properly

    // 1. Create the inner map
    let mut array_methods: HashMap<String, fn(ValueRef, MethodArgs) -> MethodReturn> =
        HashMap::new();

    let mut str_methods: HashMap<String, fn(ValueRef, MethodArgs) -> MethodReturn> = HashMap::new();

    // 2. Explicitly cast the function to the signature type
    array_methods.insert("push".to_string(), arr_push);
    array_methods.insert("pop".to_string(), arr_pop);
    array_methods.insert("get".to_string(), arr_get);
    array_methods.insert("contains".to_string(), arr_contains);
    array_methods.insert("is_empty".to_string(), arr_str_is_empty);
    array_methods.insert("insert".to_string(), arr_insert);
    array_methods.insert("empty".to_string(), arr_empty);
    attramp.insert(ValueTag::Array, array_methods);

    str_methods.insert("upper".to_string(), str_upper);
    str_methods.insert("lower".to_string(), str_lower);
    str_methods.insert("strip".to_string(), str_strip);
    str_methods.insert("is_empty".to_string(), arr_str_is_empty);
    attramp.insert(ValueTag::String, str_methods);

    attramp
});

fn arr_empty(item: ValueRef, args: MethodArgs) -> MethodReturn {
    check_method_args(args, 0, 0)?;
    match item.as_ref() {
        Value::Array(arr) => {
            arr.borrow_mut().clear();
            Ok(item.clone())
        }
        _ => Err(VmError::make_type_error("array", &item)),
    }
}

fn arr_insert(item: ValueRef, args: MethodArgs) -> MethodReturn {
    check_method_args(args, 2, 2)?;
    let idx = match args[0].as_ref() {
        Value::Integer(v) => v,
        _ => {
            return Err(VmError {
                msg: format!("Expected an integer index, got a {}", args[0].display()),
                errcode: ErrCode::TypeError,
            });
        }
    };
    match item.as_ref() {
        Value::Array(v) => {
            v.borrow_mut().insert(*idx as usize, args[1].clone());
            Ok(args[1].clone())
        }
        _ => Err(VmError::make_type_error("array", &item)),
    }
}
fn check_method_args(args: MethodArgs, min: usize, max: usize) -> Result<(), VmError> {
    let exact = min == max;
    let msg: String;
    if exact {
        msg = format!("Expected exactly {} args, got {}", min, args.len());
    } else {
        msg = format!("Expected {} to {} args, got {}", min, max, args.len());
    }
    if args.len() > max {
        return Err(VmError {
            msg,
            errcode: ErrCode::InvalidArgCount,
        });
    }
    if args.len() < min {
        return Err(VmError {
            msg,
            errcode: ErrCode::InvalidArgCount,
        });
    }
    Ok(())
}

fn arr_str_is_empty(val: ValueRef, args: MethodArgs) -> MethodReturn {
    check_method_args(args, 0, 0)?;
    match val.as_ref() {
        Value::String(v) => Ok(Rc::new(Value::Bool(v.is_empty()))),
        Value::Array(v) => Ok(Rc::new(Value::Bool(v.borrow().is_empty()))),
        _ => Err(VmError {
            msg: format!("Expected a string or array, got a {}", val.display()),
            errcode: ErrCode::TypeError,
        }),
    }
}

fn arr_get(val: Rc<Value>, args: MethodArgs) -> MethodReturn {
    check_method_args(args, 1, 2)?;
    let idx = match args[0].as_ref() {
        Value::Integer(v) => v,
        _ => {
            return Err(VmError {
                msg: format!("Expected an integer, not a {}", args[0].display()),
                errcode: ErrCode::TypeError,
            });
        }
    };
    let def = match args.get(1) {
        Some(v) => v.clone(),
        None => Rc::new(Value::Null),
    };
    match val.as_ref() {
        Value::Array(v) => match v.borrow().get(*idx as usize) {
            Some(v) => Ok(v.clone()),
            None => Ok(def),
        },
        _ => Err(VmError {
            msg: format!("Expected an array, not a {}", val.display()),
            errcode: ErrCode::TypeError,
        }),
    }
}

fn str_strip(val: Rc<Value>, _: &[Rc<Value>]) -> Result<Rc<Value>, VmError> {
    match val.as_ref() {
        Value::String(v) => Ok(Rc::new(Value::String(v.trim().to_string()))),
        _ => Err(VmError {
            msg: format!("Expected a string, not a {}.", val.display()),
            errcode: ErrCode::TypeError,
        }),
    }
}
fn str_upper(val: Rc<Value>, _: &[Rc<Value>]) -> Result<Rc<Value>, VmError> {
    match val.as_ref() {
        Value::String(v) => Ok(Rc::new(Value::String(v.to_uppercase()))),
        _ => Err(VmError {
            msg: format!("Expected a string, not a {}.", val.display()),
            errcode: ErrCode::TypeError,
        }),
    }
}

pub fn str_lower(val: Rc<Value>, _: &[Rc<Value>]) -> Result<Rc<Value>, VmError> {
    match val.as_ref() {
        Value::String(v) => Ok(Rc::new(Value::String(v.to_lowercase()))),
        _ => Err(VmError {
            msg: format!("Expected a string, not a {}.", val.display()),
            errcode: ErrCode::TypeError,
        }),
    }
}

#[cfg(test)]
mod tests {
    use core::panic;

    use super::*;

    #[test]
    fn type_checks_panic() {
        add(Value::String("hi".to_string()), Value::Float(5.0)).unwrap_err();
        add(
            Value::Func(OmniFunc::Builtin {
                name: "print".to_string(),
                func: vm_print,
            }),
            Value::Float(5.0),
        )
        .unwrap_err();
        sub(Value::String("hi".to_string()), Value::Float(5.0)).unwrap_err();
        let ltt = lt(Value::Integer(5), Value::Integer(7)).unwrap();
        match ltt {
            Value::Bool(v) => assert_eq!(v, true),
            _ => panic!("Expected the output of LT to be a boolean"),
        }
        let ltt = lt(Value::Integer(7), Value::Integer(5)).unwrap();
        match ltt {
            Value::Bool(v) => assert_eq!(v, false),
            _ => panic!("Expected the output of LT to be a boolean"),
        }
    }

    #[test]
    fn test_vm_to_str() {
        let val = Value::Integer(123);
        let res = vm_to_str(&[val]).unwrap();
        match res {
            Value::String(s) => assert_eq!(s, "123"),
            _ => panic!("Expected string"),
        }

        let val = Value::Bool(true);
        let res = vm_to_str(&[val]).unwrap();
        match res {
            Value::String(s) => assert_eq!(s, "true"),
            _ => panic!("Expected string"),
        }

        let val = Value::Null;
        let res = vm_to_str(&[val]).unwrap();
        match res {
            Value::String(s) => assert_eq!(s, "null"),
            _ => panic!("Expected string"),
        }

        let val = Value::String("hello".to_string());
        let res = vm_to_str(&[val]).unwrap();
        match res {
            Value::String(s) => assert_eq!(s, "hello"),
            _ => panic!("Expected string"),
        }
    }

    #[test]
    fn test_vm_to_int() {
        let val = Value::String("123".to_string());
        let res = vm_to_int(&[val]).unwrap();
        match res {
            Value::Integer(i) => assert_eq!(i, 123),
            _ => panic!("Expected integer"),
        }

        let val = Value::Bool(true);
        let res = vm_to_int(&[val]).unwrap();
        match res {
            Value::Integer(i) => assert_eq!(i, 1),
            _ => panic!("Expected integer"),
        }

        let val = Value::Bool(false);
        let res = vm_to_int(&[val]).unwrap();
        match res {
            Value::Integer(i) => assert_eq!(i, 0),
            _ => panic!("Expected integer"),
        }

        let val = Value::Integer(42);
        let res = vm_to_int(&[val]).unwrap();
        match res {
            Value::Integer(i) => assert_eq!(i, 42),
            _ => panic!("Expected integer"),
        }

        let val = Value::String("not a number".to_string());
        assert!(vm_to_int(&[val]).is_err());
    }

    #[test]
    fn test_vm_to_bool() {
        let val = Value::Integer(1);
        let res = vm_to_bool(&[val]).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, true),
            _ => panic!("Expected bool"),
        }

        let val = Value::Integer(0);
        let res = vm_to_bool(&[val]).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, false),
            _ => panic!("Expected bool"),
        }

        let val = Value::String("hello".to_string());
        let res = vm_to_bool(&[val]).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, true),
            _ => panic!("Expected bool"),
        }

        let val = Value::String("".to_string());
        let res = vm_to_bool(&[val]).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, false),
            _ => panic!("Expected bool"),
        }

        let val = Value::Null;
        let res = vm_to_bool(&[val]).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, false),
            _ => panic!("Expected bool"),
        }
    }

    #[test]
    fn test_vm_to_float() {
        let val = Value::Integer(123);
        let res = vm_to_float(&[val]).unwrap();
        match res {
            Value::Float(f) => assert_eq!(f, 123.0),
            _ => panic!("Expected float"),
        }

        let val = Value::String("123.45".to_string());
        let res = vm_to_float(&[val]).unwrap();
        match res {
            Value::Float(f) => assert_eq!(f, 123.45),
            _ => panic!("Expected float"),
        }

        let val = Value::Bool(true);
        let res = vm_to_float(&[val]).unwrap();
        match res {
            Value::Float(f) => assert_eq!(f, 1.0),
            _ => panic!("Expected float"),
        }

        let val = Value::Null;
        let res = vm_to_float(&[val]).unwrap();
        match res {
            Value::Float(f) => assert_eq!(f, 0.0),
            _ => panic!("Expected float"),
        }
    }

    #[test]
    fn test_add() {
        let res = add(Value::Integer(1), Value::Integer(2)).unwrap();
        match res {
            Value::Integer(i) => assert_eq!(i, 3),
            _ => panic!("Expected integer"),
        }

        let res = add(Value::Float(1.5), Value::Integer(2)).unwrap();
        match res {
            Value::Float(f) => assert_eq!(f, 3.5),
            _ => panic!("Expected float"),
        }

        let res = add(
            Value::String("a".to_string()),
            Value::String("b".to_string()),
        )
        .unwrap();
        match res {
            Value::String(s) => assert_eq!(s, "ab"),
            _ => panic!("Expected string"),
        }
    }

    #[test]
    fn test_sub() {
        let res = sub(Value::Integer(5), Value::Integer(2)).unwrap();
        match res {
            Value::Integer(i) => assert_eq!(i, 3),
            _ => panic!("Expected integer"),
        }

        let res = sub(Value::Float(5.5), Value::Integer(2)).unwrap();
        match res {
            Value::Float(f) => assert_eq!(f, 3.5),
            _ => panic!("Expected float"),
        }
    }

    #[test]
    fn test_mul() {
        let res = mul(Value::Integer(2), Value::Integer(3)).unwrap();
        match res {
            Value::Integer(i) => assert_eq!(i, 6),
            _ => panic!("Expected integer"),
        }

        let res = mul(Value::String("a".to_string()), Value::Integer(3)).unwrap();
        match res {
            Value::String(s) => assert_eq!(s, "aaa"),
            _ => panic!("Expected string"),
        }
    }

    #[test]
    fn test_div() {
        let res = div(Value::Integer(6), Value::Integer(3)).unwrap();
        match res {
            Value::Integer(i) => assert_eq!(i, 2),
            _ => panic!("Expected integer"),
        }

        let res = div(Value::Float(7.0), Value::Float(2.0)).unwrap();
        match res {
            Value::Float(f) => assert_eq!(f, 3.5),
            _ => panic!("Expected float"),
        }
    }

    #[test]
    fn test_pow() {
        let res = pow(Value::Integer(2), Value::Integer(3)).unwrap();
        match res {
            Value::Integer(i) => assert_eq!(i, 8),
            _ => panic!("Expected integer"),
        }
    }

    #[test]
    fn test_comparisons() {
        // LT
        let res = lt(Value::Integer(2), Value::Integer(3)).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, true),
            _ => panic!("Expected bool"),
        }
        // GT
        let res = gt(Value::Integer(3), Value::Integer(2)).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, true),
            _ => panic!("Expected bool"),
        }
        // LTE
        let res = lte(Value::Integer(2), Value::Integer(2)).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, true),
            _ => panic!("Expected bool"),
        }
        // GTE
        let res = gte(Value::Integer(3), Value::Integer(3)).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, true),
            _ => panic!("Expected bool"),
        }
        // EQ
        let res = equal_to(Value::Integer(3), Value::Integer(3)).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, true),
            _ => panic!("Expected bool"),
        }
    }

    #[test]
    fn test_logical() {
        // OR
        let res = or(Value::Bool(true), Value::Bool(false)).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, true),
            _ => panic!("Expected bool"),
        }
        // AND
        let res = and(Value::Bool(true), Value::Bool(false)).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, false),
            _ => panic!("Expected bool"),
        }
    }
}
