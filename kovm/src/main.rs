use clap::{Parser, Subcommand};
use owo_colors::OwoColorize;
use std::process::exit;
use std::fs;
mod runtime;
mod vm;
use vm::VM;

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
            exit(opt);
        }
        Err(e) => {
            // Single, clear error line at the top.
            println!("{}: {}\n", e.errcode.to_string().red().bold(), e.msg.red());
            println!("{}", "Traceback (most recent call last):".bold());
            let lines_opt = vm.lines.as_ref();
            let source_opt = vm.sources;

            for (frame_idx, frame) in vm.frames.iter().rev().enumerate() {
                if frame_idx > 0 {
                    println!()
                } // Add space between frames

                // Frame location info
                let source_num = vm.source_select.get(frame.i);
                let ip_str_val = format!("ins 0x{:04X} ({})", frame.i, frame.i);
                let ip_str = ip_str_val.dimmed();

                if let Some(lines) = lines_opt {
                    if let Some(&line_nr_64) = lines.get(frame.i) {
                        let line_nr = line_nr_64 as usize;

                        // Code snippet
                        if let Some(select) = source_num {
                            if let Some(source) = source_opt.get(*select) {
                                println!(
                                    "  at {} ({}:{})",
                                    frame.name.cyan(),
                                    source.fp,
                                    (line_nr + 1).to_string().green()
                                );
                                println!("  {}", ip_str);

                                let radius = 4;
                                let start = line_nr.saturating_sub(radius);
                                let end = std::cmp::min(line_nr + radius + 1, source.content.len());

                                println!(); // Spacer before code
                                for i in start..end {
                                    let line_prefix_val = format!("{:>4} |", i + 1);
                                    let line_prefix = line_prefix_val.blue();
                                    if i == line_nr {
                                        println!(
                                            "{} {} {}",
                                            "->".red().bold(),
                                            line_prefix,
                                            source.content[i].bold().underline()
                                        );
                                    } else {
                                        println!("   {} {}", line_prefix, &source.content[i]);
                                    }
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
