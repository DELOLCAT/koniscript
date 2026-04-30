use crate::vm::{FncExit, VM};
use once_cell::sync::Lazy;
use std::cell::RefCell;
use std::collections::HashMap;
use std::fmt;
use std::io::{self, Write};
use std::rc::Rc;
use std::thread::sleep;
pub type MethodArgs<'a> = &'a [Value];
pub type MethodReturn = Result<Value, VmError>;

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
    pub val: Value,
}
#[derive(Debug, Clone)]
pub struct Env {
    pub values: Vec<Option<Value>>,
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
    String(Rc<String>),
    Bool(bool),
    Func(Rc<KoniFunc>),
    Float(f64),
    Module(Rc<Module>),
    Array(Rc<RefCell<Vec<Value>>>),
    Null,
    RuntimeValue(RuntimeType),
    Dict(Rc<Vec<(Value, Value)>>),
    CallRequest(Rc<KoniFunc>, Rc<Vec<Value>>),
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
        (Value::Func(a), Value::Func(b)) => Ok(a == b),
        _ => Err(()),
    }
}

impl PartialEq for KoniFunc {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (
                KoniFunc::User {
                    name: a,
                    module: ma,
                    ..
                },
                KoniFunc::User {
                    name: b,
                    module: mb,
                    ..
                },
            ) => a == b && ma == mb,
            (KoniFunc::Builtin { name: a, .. }, KoniFunc::Builtin { name: b, .. }) => a == b,
            (KoniFunc::BuiltinMethod { name: a, .. }, KoniFunc::BuiltinMethod { name: b, .. }) => {
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
                let out = vm_to_int_basic(&Value::String(Rc::new(payload.to_string())))?;
                Ok(out)
            }
            ValueTag::Bool => {
                let out: Value;
                if payload == "1" || payload == "true" {
                    out = Value::Bool(true)
                } else {
                    out = Value::Bool(false);
                }
                Ok(out)
            }
            ValueTag::Null => Ok(Value::Null),
            ValueTag::String => Ok(Value::String(Rc::new(payload.to_string()))),
            ValueTag::Float => {
                let out = vm_to_float_basic(&Value::String(Rc::new(payload.to_string())))?;
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
            Value::Func(f) => match &**f {
                KoniFunc::User { entry, name, .. } => format!("[function {} at {}]", name, entry),
                KoniFunc::Builtin { name, .. } => format!("[builtin function {}]", name),
                KoniFunc::BuiltinMethod { name, .. } => format!("builtin method {}]", name),
            },
            Value::Null => "null".to_string(),
            Value::Module(m) => format!("[module {}]", m.name),
            Value::Array(_) => "array".to_string(),
            Value::RuntimeValue(r) => format!("[runtime value '{}']", r.name()), // This should never be called
            Value::Dict(_) => {
                match self
                    .dict_get(&Value::String(Rc::new("_display_type".to_string())))
                    .unwrap()
                {
                    None => "dict".to_string(),
                    Some(v) => match v {
                        Value::String(s) => s.to_string(),
                        _ => "dict".to_string(),
                    },
                }
            }
            Value::CallRequest(r, _) => {
                format!(
                    "[call request for {}]",
                    Value::Func(Rc::new(r.as_ref().clone())).display()
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
            Value::Func(v) => match &**v {
                KoniFunc::Builtin { name, .. } => format!("<builtin func {}>", name),
                KoniFunc::User { entry, name, .. } => format!("<func {}() at ins {}>", name, entry),
                KoniFunc::BuiltinMethod { name, .. } => format!("<builtin method {}>", name),
            },
            Value::Module(v) => {
                format!("<module {} with {} exports>", v.name, v.exports.len())
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
            Value::Dict(_) => match self
                .dict_get(&Value::String(Rc::new("_repr".to_string())))
                .unwrap()
            {
                Some(v) => match v {
                    Value::String(v) => v.to_string(),
                    _ => self.dict_display().unwrap(),
                },
                _ => self.dict_display().unwrap(),
            },
            Value::CallRequest(_, _) => panic!("Illegal value received for repr()"), // It should've been converted on call
        }
    }
    pub fn dict_get(&self, key: &Value) -> Result<Option<Value>, VmError> {
        match self {
            Value::Dict(d) => {
                for (k, v) in d.iter() {
                    if k == key {
                        return Ok(Some(v.clone()));
                    }
                }
                Ok(None)
            }
            _ => Err(VmError::make_type_error("dict", self)),
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
            _ => Err(VmError::make_type_error("dict", self)),
        }
    }
}
#[derive(Debug, Clone)]
pub enum KoniFunc {
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
        func: fn(run_func: &mut VM, &[Value]) -> Result<Value, VmError>,
    },
    BuiltinMethod {
        name: String,
        func: fn(Value, &[Value]) -> Result<Value, VmError>,
    },
}
#[repr(i32)]
#[derive(Debug)]
pub enum ErrCode {
    InvalidArgCount = 1,
    ConversionNotPossible = 2,
    ConversionFailed = 3,
    IoError = 4,
    InvalidBytecode = 5,
    VariableNotFound = 6,
    StackUnderflow = 7,
    TypeError = 8,
    FuncNameStr = 9,
    InvalidLocal = 10,
    CompatibilityError = 11,
    NoCode = 12,
    ValueError = 13,
    AttributeError = 14,
    ExitSignal(i32) = 15,
    InvalidOperation = 16,
    IndexError = 17,
    MathError = 18,
}
impl fmt::Display for ErrCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:?}", self)
    }
}

pub fn vm_to_str(_vm: &mut VM, args: &[Value]) -> Result<Value, VmError> {
    let [item] = args else {
        return Err(VmError {
            msg: format!("Expected 1 argument, got {}", args.len()),
            errcode: ErrCode::InvalidArgCount,
        });
    };
    match vm_to_str_basic(item) {
        Ok(v) => Ok(v),
        Err(e) => match item {
            Value::Dict(d) => match item.dict_get(&Value::String(Rc::new("_str".to_string())))? {
                Some(v) => match &v {
                    Value::Func(f) => match _vm.run_function(v, vec![item.clone()])? {
                        FncExit::Exit(v) => {
                            return Err(VmError {
                                msg: "".to_string(),
                                errcode: ErrCode::ExitSignal(v),
                            });
                        }
                        FncExit::Returned(f) => return Ok(f.clone()),
                        FncExit::None => todo!(),
                    },
                    _ => todo!(),
                },
                _ => todo!(),
            },
            _ => todo!(),
        },
    }
}
fn vm_to_str_basic(item: &Value) -> Result<Value, VmError> {
    match item {
        Value::Integer(val) => Result::Ok(Value::String(Rc::new(val.to_string()))),
        Value::Float(val) => Result::Ok(Value::String(Rc::new(val.to_string()))),
        Value::Bool(val) => {
            if *val {
                Result::Ok(Value::String(Rc::new("true".to_string())))
            } else {
                Result::Ok(Value::String(Rc::new("false".to_string())))
            }
        }
        Value::Func(_) => Ok(Value::String(Rc::new(item.repr()))),
        Value::String(val) => Result::Ok(Value::String(Rc::new(val.to_string()))),
        Value::Null => Result::Ok(Value::String(Rc::new("null".to_string()))),
        Value::Array(_) => Ok(Value::String(Rc::new(item.repr()))),
        Value::Module(_) => Ok(Value::String(Rc::new(item.repr()))),
        Value::Dict(_) => match item.dict_get(&Value::String(Rc::new("_str".to_string()))).unwrap() {
            Some(v) => match v {
                Value::String(v) => Ok(Value::String(Rc::new(v.to_string()))),
                _ => Ok(Value::String(Rc::new(item.dict_display()?))),
            },
            _ => Ok(Value::String(Rc::new(item.dict_display()?))),
        },
        _ => {
            return Err(VmError {
                msg: format!("Illegal value received for repr(): {}", item.display()),
                errcode: ErrCode::TypeError,
            });
        }
    }
}
pub fn vm_to_float(_vm: &mut VM, args: &[Value]) -> Result<Value, VmError> {
    let [item] = args else {
        return Err(VmError {
            msg: format!("Expected 1 argument, got {}", args.len()),
            errcode: ErrCode::InvalidArgCount,
        });
    };
    vm_to_float_basic(item)
}

fn vm_to_float_basic(item: &Value) -> Result<Value, VmError> {
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
pub fn vm_to_int(_vm: &mut VM, args: &[Value]) -> Result<Value, VmError> {
    let [item] = args else {
        return Err(VmError {
            msg: format!("Expected 1 argument, got {}", args.len()),
            errcode: ErrCode::InvalidArgCount,
        });
    };

    vm_to_int_basic(item)
}
fn vm_to_int_basic(item: &Value) -> Result<Value, VmError> {
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

pub fn vm_to_bool(_vm: &mut VM, args: &[Value]) -> Result<Value, VmError> {
    let [item] = args else {
        return Err(VmError {
            msg: format!("Expected 1 argument, got {}", args.len()),
            errcode: ErrCode::InvalidArgCount,
        });
    };
    vm_to_bool_basic(item)
}
pub fn vm_to_bool_basic(item: &Value) -> Result<Value, VmError> {
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
pub fn vm_println(_vm: &mut VM, args: &[Value]) -> Result<Value, VmError> {
    print_helper(_vm, args)?;
    println!();
    Ok(Value::Null)
}
fn print_helper(_vm: &mut VM, args: &[Value]) -> Result<(), VmError> {
    let mut rust_args: Vec<String> = Vec::new();
    for item in args {
        let out = vm_to_str(_vm, std::slice::from_ref(item));
        match out {
            Ok(val) => {
                if let Value::String(v) = val {
                    rust_args.push(v.to_string());
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
pub fn vm_print(_vm: &mut VM, args: &[Value]) -> Result<Value, VmError> {
    print_helper(_vm, args)?;
    io::stdout().flush().map_err(|e| VmError {
        msg: format!("Failed to flush stdout: {}", e),
        errcode: ErrCode::IoError, // Or a specific I/O error code
    })?;

    Ok(Value::Null)
}
pub fn vm_sleep(_vm: &mut VM, args: &[Value]) -> Result<Value, VmError> {
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
                errcode: ErrCode::TypeError,
            });
        }
    }
    Ok(Value::Null)
}

pub fn vm_input(_vm: &mut VM, args: &[Value]) -> Result<Value, VmError> {
    let [_prompt] = args else {
        return Err(VmError {
            msg: format!("Expected 1 argument, got {}", args.len()),
            errcode: ErrCode::InvalidArgCount,
        });
    };

    let prompt = match vm_to_str(_vm, args)? {
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

    Ok(Value::String(Rc::new(buf)))
}
pub fn vm_hi(_vm: &mut VM, _args: &[Value]) -> Result<Value, VmError> {
    println!("hi from math");
    Ok(Value::Null)
}
pub fn vmenv() -> Vec<Value> {
    vec![
        Value::Func(Rc::new(KoniFunc::Builtin {
            name: "print".to_string(),
            func: vm_print,
        })),
        Value::Func(Rc::new(KoniFunc::Builtin {
            name: "println".to_string(),
            func: vm_println,
        })),
        Value::Func(Rc::new(KoniFunc::Builtin {
            name: "sleep".to_string(),
            func: vm_sleep,
        })),
        Value::Func(Rc::new(KoniFunc::Builtin {
            name: "input".to_string(),
            func: vm_input,
        })),
        Value::Func(Rc::new(KoniFunc::Builtin {
            name: "to_str".to_string(),
            func: vm_to_str,
        })),
        Value::Func(Rc::new(KoniFunc::Builtin {
            name: "to_int".to_string(),
            func: vm_to_int,
        })),
        Value::Func(Rc::new(KoniFunc::Builtin {
            name: "to_bool".to_string(),
            func: vm_to_bool,
        })),
        Value::Func(Rc::new(KoniFunc::Builtin {
            name: "to_float".to_string(),
            func: vm_to_float,
        })),
        Value::Func(Rc::new(KoniFunc::Builtin {
            name: "exit".to_string(),
            func: vm_exit,
        })),
        Value::Func(Rc::new(KoniFunc::Builtin {
            name: "len".to_string(),
            func: vm_len,
        })),
        Value::Module(Rc::new(Module {
            exports: HashMap::from([(
                "hi".to_string(),
                Export {
                    name: "math".to_string(),
                    val: Value::Func(Rc::new(KoniFunc::Builtin {
                        name: "hi".to_string(),
                        func: vm_hi,
                    })),
                },
            )]),
            name: "math".to_string(),
        })),
        Value::RuntimeValue(RuntimeType::Name),
    ]
}

fn vm_exit(_vm: &mut VM, args: &[Value]) -> Result<Value, VmError> {
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

fn vm_len(_vm: &mut VM, args: &[Value]) -> Result<Value, VmError> {
    expect_args(args, 1)?;
    match &args[0] {
        Value::String(v) => Ok(Value::Integer(v.len().try_into().unwrap())),
        Value::Array(v) => Ok(Value::Integer(v.borrow().len().try_into().unwrap())),
        Value::Dict(d) => {
            match args[0]
                .dict_get(&Value::String(Rc::new("_len".to_string())))
                .unwrap()
            {
                None => Ok(Value::Integer(d.len().try_into().unwrap())),
                Some(v) => match v {
                    Value::Func(v) => Ok(Value::CallRequest(
                        v.clone(),
                        Rc::new(vec![args[0].clone()]),
                    )), // TODO: perhaps find out how to not clone this
                    Value::Integer(v) => Ok(Value::Integer(v)),
                    _ => Ok(Value::Integer(d.len().try_into().unwrap())),
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
            Ok(Value::String(out.into()))
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
        (Value::Integer(va), Value::Integer(vb)) => {
            if *vb == 0 {
                Err(VmError {
                    msg: "Attempted to divide by 0".to_string(),
                    errcode: ErrCode::MathError,
                })
            } else {
                Ok(Value::Integer(va / vb))
            }
        }
        (Value::Float(va), Value::Integer(vb)) => {
            if *vb == 0 {
                Err(VmError {
                    msg: "Attempted to divide by 0".to_string(),
                    errcode: ErrCode::MathError,
                })
            } else {
                Ok(Value::Float(va / *vb as f64))
            }
        }

        (Value::Integer(va), Value::Float(vb)) => {
            if *vb == 0.0 {
                Err(VmError {
                    msg: "Attempted to divide by 0".to_string(),
                    errcode: ErrCode::MathError,
                })
            } else {
                Ok(Value::Float(*va as f64 / vb))
            }
        }
        (Value::Float(va), Value::Float(vb)) => {
            if *vb == 0.0 {
                Err(VmError {
                    msg: "Attempted to divide by 0".to_string(),
                    errcode: ErrCode::MathError,
                })
            } else {
                Ok(Value::Float(va / vb))
            }
        }

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
        (Value::Integer(va), Value::Integer(vb)) => {
            if *vb == 0 {
                Err(VmError {
                    msg: "Attempted to modulo by 0".to_string(),
                    errcode: ErrCode::MathError,
                })
            } else {
                Ok(Value::Integer(va % vb))
            }
        }
        (Value::Float(va), Value::Integer(vb)) => {
            if *vb == 0 {
                Err(VmError {
                    msg: "Attempted to modulo by 0".to_string(),
                    errcode: ErrCode::MathError,
                })
            } else {
                Ok(Value::Float(va % *vb as f64))
            }
        }

        (Value::Integer(va), Value::Float(vb)) => {
            if *vb == 0.0 {
                Err(VmError {
                    msg: "Attempted to modulo by 0".to_string(),
                    errcode: ErrCode::MathError,
                })
            } else {
                Ok(Value::Float(*va as f64 % vb))
            }
        }
        (Value::Float(va), Value::Float(vb)) => {
            if *vb == 0.0 {
                Err(VmError {
                    msg: "Attempted to modulo by 0".to_string(),
                    errcode: ErrCode::MathError,
                })
            } else {
                Ok(Value::Float(va % vb))
            }
        }

        _ => Err(VmError {
            msg: format!(
                "TypeError: Cannot modulo a {} with a {}",
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
            Ok(Value::String(Rc::new(out)))
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
fn arr_pop(item: Value, args: &[Value]) -> Result<Value, VmError> {
    expect_args(args, 0)?;
    match item {
        Value::Array(ar) => match ar.borrow_mut().pop() {
            Some(v) => Ok(v.into()),
            None => Err(VmError {
                msg: "Cannot `pop()` from an empty array".to_string(),
                errcode: ErrCode::InvalidOperation,
            }),
        },
        _ => Err(VmError::make_type_error("array", &item)),
    }
}
fn arr_contains(item: Value, args: &[Value]) -> Result<Value, VmError> {
    expect_args(args, 1)?;
    let cont = &args[0];
    match item {
        Value::Array(arr) => Ok(Value::Bool(arr.borrow().contains(cont))),
        _ => Err(VmError::make_type_error("array", &item)),
    }
}
fn arr_push(item: Value, args: &[Value]) -> Result<Value, VmError> {
    expect_args(args, 1)?;

    match &item {
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
    HashMap<ValueTag, HashMap<String, fn(Value, &[Value]) -> Result<Value, VmError>>>,
> = Lazy::new(|| {
    let mut attramp = HashMap::new(); // Initialize properly

    // 1. Create the inner map
    let mut array_methods: HashMap<String, fn(Value, MethodArgs) -> MethodReturn> =
        HashMap::new();

    let mut str_methods: HashMap<String, fn(Value, MethodArgs) -> MethodReturn> = HashMap::new();

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

fn arr_empty(item: Value, args: MethodArgs) -> MethodReturn {
    check_method_args(args, 0, 0)?;
    match &item {
        Value::Array(arr) => {
            arr.borrow_mut().clear();
            Ok(item)
        }
        _ => Err(VmError::make_type_error("array", &item)),
    }
}

fn arr_insert(item: Value, args: MethodArgs) -> MethodReturn {
    check_method_args(args, 2, 2)?;
    let idx = match args[0] {
        Value::Integer(v) => v,
        _ => {
            return Err(VmError {
                msg: format!("Expected an integer index, got a {}", args[0].display()),
                errcode: ErrCode::TypeError,
            });
        }
    };
    match item {
        Value::Array(v) => {
            v.borrow_mut().insert(idx as usize, args[1].clone());
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

fn arr_str_is_empty(val: Value, args: MethodArgs) -> MethodReturn {
    check_method_args(args, 0, 0)?;
    match val {
        Value::String(v) => Ok(Value::Bool(v.is_empty())),
        Value::Array(v) => Ok(Value::Bool(v.borrow().is_empty())),
        _ => Err(VmError {
            msg: format!("Expected a string or array, got a {}", val.display()),
            errcode: ErrCode::TypeError,
        }),
    }
}

fn arr_get(val: Value, args: MethodArgs) -> MethodReturn {
    check_method_args(args, 1, 2)?;
    let idx = match args[0] {
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
        None => Value::Null,
    };
    match val {
        Value::Array(v) => match v.borrow().get(idx as usize) {
            Some(v) => Ok(v.clone()),
            None => Ok(def),
        },
        _ => Err(VmError::make_type_error("array", &val)),
    }
}

fn str_strip(val: Value, _: &[Value]) -> Result<Value, VmError> {
    match val {
        Value::String(v) => Ok(Value::String(Rc::new(v.trim().to_string()))),
        _ => Err(VmError::make_type_error("str", &val)),
    }
}
fn str_upper(val: Value, _: &[Value]) -> Result<Value, VmError> {
    match val {
        Value::String(v) => Ok(Value::String(Rc::new(v.to_uppercase()))),
        _ => Err(VmError::make_type_error("str", &val)),
    }
}

pub fn str_lower(val: Value, _: &[Value]) -> Result<Value, VmError> {
    match val {
        Value::String(v) => Ok(Value::String(Rc::new(v.to_lowercase()))),
        _ => Err(VmError::make_type_error("str", &val)),
    }
}

#[cfg(test)]
mod tests {
    use core::panic;

    use super::*;

    #[test]
    fn type_checks_panic() {
        add(Value::String(Rc::new("hi".to_string())), Value::Float(5.0)).unwrap_err();
        add(
            Value::Func(Rc::new(KoniFunc::Builtin {
                name: "print".to_string(),
                func: vm_print,
            })),
            Value::Float(5.0),
        )
        .unwrap_err();
        sub(Value::String(Rc::new("hi".to_string())), Value::Float(5.0)).unwrap_err();
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
        let res = vm_to_str_basic(&val).unwrap();
        match res {
            Value::String(s) => assert_eq!(*s, "123"),
            _ => panic!("Expected string"),
        }

        let val = Value::Bool(true);
        let res = vm_to_str_basic(&val).unwrap();
        match res {
            Value::String(s) => assert_eq!(*s, "true"),
            _ => panic!("Expected string"),
        }

        let val = Value::Null;
        let res = vm_to_str_basic(&val).unwrap();
        match res {
            Value::String(s) => assert_eq!(*s, "null"),
            _ => panic!("Expected string"),
        }

        let val = Value::String(Rc::new("hello".to_string()));
        let res = vm_to_str_basic(&val).unwrap();
        match res {
            Value::String(s) => assert_eq!(*s, "hello"),
            _ => panic!("Expected string"),
        }
    }

    #[test]
    fn test_vm_to_int() {
        let val = Value::String(Rc::new("123".to_string()));
        let res = vm_to_int_basic(&val).unwrap();
        match res {
            Value::Integer(i) => assert_eq!(i, 123),
            _ => panic!("Expected integer"),
        }

        let val = Value::Bool(true);
        let res = vm_to_int_basic(&val).unwrap();
        match res {
            Value::Integer(i) => assert_eq!(i, 1),
            _ => panic!("Expected integer"),
        }

        let val = Value::Bool(false);
        let res = vm_to_int_basic(&val).unwrap();
        match res {
            Value::Integer(i) => assert_eq!(i, 0),
            _ => panic!("Expected integer"),
        }

        let val = Value::Integer(42);
        let res = vm_to_int_basic(&val).unwrap();
        match res {
            Value::Integer(i) => assert_eq!(i, 42),
            _ => panic!("Expected integer"),
        }

        let val = Value::String(Rc::new("not a number".to_string()));
        assert!(vm_to_int_basic(&val).is_err());
    }

    #[test]
    fn test_vm_to_bool() {
        let val = Value::Integer(1);
        let res = vm_to_bool_basic(&val).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, true),
            _ => panic!("Expected bool"),
        }

        let val = Value::Integer(0);
        let res = vm_to_bool_basic(&val).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, false),
            _ => panic!("Expected bool"),
        }

        let val = Value::String(Rc::new("hello".to_string()));
        let res = vm_to_bool_basic(&val).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, true),
            _ => panic!("Expected bool"),
        }

        let val = Value::String(Rc::new("".to_string()));
        let res = vm_to_bool_basic(&val).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, false),
            _ => panic!("Expected bool"),
        }

        let val = Value::Null;
        let res = vm_to_bool_basic(&val).unwrap();
        match res {
            Value::Bool(b) => assert_eq!(b, false),
            _ => panic!("Expected bool"),
        }
    }

    #[test]
    fn test_vm_to_float() {
        let val = Value::Integer(123);
        let res = vm_to_float_basic(&val).unwrap();
        match res {
            Value::Float(f) => assert_eq!(f, 123.0),
            _ => panic!("Expected float"),
        }

        let val = Value::String(Rc::new("123.45".to_string()));
        let res = vm_to_float_basic(&val).unwrap();
        match res {
            Value::Float(f) => assert_eq!(f, 123.45),
            _ => panic!("Expected float"),
        }

        let val = Value::Bool(true);
        let res = vm_to_float_basic(&val).unwrap();
        match res {
            Value::Float(f) => assert_eq!(f, 1.0),
            _ => panic!("Expected float"),
        }

        let val = Value::Null;
        let res = vm_to_float_basic(&val).unwrap();
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
            Value::String(Rc::new("a".to_string())),
            Value::String(Rc::new("b".to_string())),
        )
        .unwrap();
        match res {
            Value::String(s) => assert_eq!(*s, "ab"),
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

        let res = mul(Value::String(Rc::new("a".to_string())), Value::Integer(3)).unwrap();
        match res {
            Value::String(s) => assert_eq!(s, Rc::new("aaa".to_string())),
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
