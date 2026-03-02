use once_cell::sync::Lazy;
use std::cell::RefCell;
use std::collections::HashMap;
use std::fmt;
use std::io::{self, Write};
use std::rc::Rc;
use std::thread::sleep;

pub type ValueRef = Rc<Value>;


pub static SUPPORTED_FEATURES: Lazy<Vec<String>> = Lazy::new(|| vec!["fs".to_string(), "string_methods".to_string()]);
#[derive(Debug, Clone)]
pub struct Env {
    pub values: Vec<Option<ValueRef>>,
    pub parent: Option<Rc<RefCell<Env>>>,
    pub exports: HashMap<String, ValueRef>,
}
#[derive(Debug, Clone)]
pub struct Module {
    pub exports: HashMap<String, ValueRef>,
    pub name: Option<String>,
}
#[derive(Debug)]
pub struct VmError {
    pub msg: String,
    pub errcode: ErrCode,
}
#[derive(Debug)]
pub enum VmPanic {
    TagConversionFailed,
    UnexpectedValue,
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
    Float(f64),
    Module(Module),
    Array(Rc<RefCell<Vec<ValueRef>>>),
    Null,
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
                LsFunc::User { entry, name, .. } => format!("[function {} at {}]", name, entry),
                LsFunc::Builtin { name, .. } => format!("[builtin function {}]", name),
                LsFunc::BuiltinMethod { name, .. } => format!("builtin method {}]", name),
            },
            Value::Null => "null".to_string(),
            Value::Module(m) => match &m.name {
                Some(v) => format!("[module {}]", v),
                None => "[module]".to_string(),
            },
            Value::Array(_) => "array".to_string(),
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
            Value::Null => ValueTag::Null
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
        name: String,
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
            LsFunc::Builtin { name, .. } => {
                let out = format!("[builtin func {}]", name);
                Result::Ok(Value::String(out))
            }
            LsFunc::User { entry, name, .. } => {
                let out = format!("[func {} at ins {}]", name, entry);
                Result::Ok(Value::String(out))
            }
            LsFunc::BuiltinMethod { name, .. } => {
                let out = format!("[builtin method {}]", name);
                Ok(Value::String(out))
            }
        },
        Value::String(val) => Result::Ok(Value::String(val.to_string())),
        Value::Null => Result::Ok(Value::String("null".to_string())),
        Value::Array(items_rc) => {
            let items = items_rc.borrow();
            let mut output = "[".to_string();
            let mut first = true;
            for item in items.iter() {
                if !first {
                    output.push_str(", ");
                }
                let asstr = match vm_to_str(std::slice::from_ref(item)) {
                    Ok(v) => {
                        if let Value::String(val) = v {
                            val
                        } else {
                            unreachable!("vm_to_str must return a string")
                        }
                    }
                    Err(e) => return Err(e),
                };
                output.push_str(&asstr);
                first = false;
            }
            output.push(']');
            Ok(Value::String(output))
        }
        Value::Module(v) => {
            if v.name.is_some() {
                Ok(Value::String(format!(
                    "[module {} with {} exports]",
                    v.name.as_ref().unwrap(),
                    v.exports.len()
                )))
            } else {
                Ok(Value::String(format!(
                    "[module with {} exports]",
                    v.exports.len()
                )))
            }
        }
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
pub fn vm_print(args: &[Value]) -> Result<Value, VmError> {
    let mut rust_args: Vec<String> = Vec::new();
    for item in args {
        let out = vm_to_str(std::slice::from_ref(item));
        match out {
            Ok(val) => {
                if let Value::String(v) = val {
                    rust_args.push(v);
                } else {
                    return Err(VmError {
                        msg: "Could not convert to string".to_string(),
                        errcode: ErrCode::ConversionFailed,
                    });
                }
            }
            Err(e) => return Err(e),
        }
    }

    println!("{}", rust_args.join(" "));
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
        Value::Func(LsFunc::Builtin {
            name: "print".to_string(),
            func: vm_print,
        }),
        Value::Func(LsFunc::Builtin {
            name: "sleep".to_string(),
            func: vm_sleep,
        }),
        Value::Func(LsFunc::Builtin {
            name: "input".to_string(),
            func: vm_input,
        }),
        Value::Func(LsFunc::Builtin {
            name: "to_str".to_string(),
            func: vm_to_str,
        }),
        Value::Func(LsFunc::Builtin {
            name: "to_int".to_string(),
            func: vm_to_int,
        }),
        Value::Func(LsFunc::Builtin {
            name: "to_bool".to_string(),
            func: vm_to_bool,
        }),
        Value::Func(LsFunc::Builtin {
            name: "to_float".to_string(),
            func: vm_to_float,
        }),
        Value::Module(Module {
            exports: HashMap::from([(
                "hi".to_string(),
                Rc::new(Value::Func(LsFunc::Builtin {
                    name: "hi".to_string(),
                    func: vm_hi,
                })),
            )]),
            name: Some("math".to_string()),
        }),
    ]
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
    match (&a, &b) {
        (Value::Integer(va), Value::Integer(vb)) => Ok(Value::Bool(va == vb)),
        (Value::Bool(va), Value::Bool(vb)) => Ok(Value::Bool(va == vb)),
        (Value::Integer(va), Value::Float(vb)) => Ok(Value::Bool(*va as f64 == *vb)),
        (Value::Float(va), Value::Integer(vb)) => Ok(Value::Bool(*va == *vb as f64)),
        (Value::Float(va), Value::Float(vb)) => Ok(Value::Bool(va == vb)),
        (Value::String(va), Value::String(vb)) => Ok(Value::Bool(va == vb)),

        _ => Err(VmError {
            msg: format!(
                "TypeError: Cannot check if a {} is equal to a {}",
                a.display(),
                b.display()
            ),
            errcode: ErrCode::TypeError,
        }),
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
    fs.insert("MULTIPLY".to_string(), mul);
    fs.insert("DIV".to_string(), div);
    fs.insert("SUBTRACT".to_string(), sub);
    fs.insert("POW".to_string(), pow);
    fs.insert("LESS_THAN".to_string(), lt);
    fs.insert("GREATER_THAN".to_string(), gt);
    fs.insert("GREATER_THAN_OR_EQ".to_string(), gte);
    fs.insert("LESS_THAN_OR_EQ".to_string(), lte);
    fs.insert("EQUAL_TO".to_string(), equal_to);
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
    let mut array_methods: HashMap<
        String,
        fn(Rc<Value>, &[Rc<Value>]) -> Result<Rc<Value>, VmError>,
    > = HashMap::new();

    let mut str_methods: HashMap<
        String,
        fn(Rc<Value>, &[Rc<Value>]) -> Result<Rc<Value>, VmError>,
    > = HashMap::new();

    // 2. Explicitly cast the function to the signature type
    array_methods.insert("push".to_string(), arr_push);
    attramp.insert(ValueTag::Array, array_methods);

    str_methods.insert("upper".to_string(), str_upper);
    str_methods.insert("lower".to_string(), str_lower);
    str_methods.insert("strip".to_string(), str_strip);
    attramp.insert(ValueTag::String, str_methods);

    attramp
});

fn str_strip(val: Rc<Value>, _: &[Rc<Value>]) -> Result<Rc<Value>, VmError> {
    match val.as_ref() {
        Value::String(v) => Ok(Rc::new(Value::String(v.trim().to_string()))),
        _ => Err(
            VmError {
                msg: format!("Expected a string, not a {}.", val.display()),
                errcode: ErrCode::TypeError
            }
        )
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
            Value::Func(LsFunc::Builtin {
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
