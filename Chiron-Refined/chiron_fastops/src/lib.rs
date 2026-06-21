//! Chiron native hot-path (optional). Owner: Jacob Iannotti.
//!
//! Exact kernels exposed over the C ABI so `fastops.py` can load them via ctypes.
//! The Python side ALWAYS has a pure-Python fallback, so the engine runs with or
//! without this library — native is an accelerator, never a dependency. The same
//! crate compiles to WebAssembly (`wasm32-unknown-unknown`) for in-browser use by
//! the offline dashboard.

use std::os::raw::{c_int, c_longlong};
use std::slice;

/// Finite-difference degree of an integer sequence (-1 if not polynomial).
/// Exact in i128; the hot inner step of polynomial recovery.
#[no_mangle]
pub extern "C" fn chiron_poly_degree(ptr: *const c_longlong, n: c_int) -> c_longlong {
    if ptr.is_null() || n <= 0 {
        return -1;
    }
    let n = n as usize;
    let src = unsafe { slice::from_raw_parts(ptr, n) };
    let mut a: Vec<i128> = src.iter().map(|&x| x as i128).collect();
    let mut m = n;
    for l in 0..n {
        if a[..m].iter().all(|&x| x == a[0]) {
            return l as c_longlong;
        }
        for i in 0..m - 1 {
            a[i] = a[i + 1] - a[i];
        }
        m -= 1;
        if m == 0 {
            break;
        }
    }
    -1
}

fn feet_ok(q: &[u8]) -> bool {
    // q: 1 = long, 0 = short. Six feet:
    //   feet 1-5 (idx 0..=4): dactyl (1,0,0) or spondee (1,1)
    //   foot 6  (idx 5):      spondee (1,1) or trochee (1,0)  [final anceps]
    fn rec(q: &[u8], pos: usize, foot: usize) -> bool {
        if foot == 6 {
            return pos == q.len();
        }
        // dactyl, feet 1..5
        if foot <= 4 && pos + 3 <= q.len() && q[pos] == 1 && q[pos + 1] == 0 && q[pos + 2] == 0
            && rec(q, pos + 3, foot + 1)
        {
            return true;
        }
        // spondee, any foot
        if pos + 2 <= q.len() && q[pos] == 1 && q[pos + 1] == 1 && rec(q, pos + 2, foot + 1) {
            return true;
        }
        // trochee, only the final foot
        if foot == 5 && pos + 2 <= q.len() && q[pos] == 1 && q[pos + 1] == 0
            && rec(q, pos + 2, foot + 1)
        {
            return true;
        }
        false
    }
    rec(q, 0, 0)
}

/// Does a quantity string segment into six dactylic-hexameter feet?
/// `ptr` points at bytes where 1 = long syllable, 0 = short. Returns 1/0.
#[no_mangle]
pub extern "C" fn chiron_hexameter_feet_ok(ptr: *const u8, n: c_int) -> c_int {
    if ptr.is_null() || n <= 0 {
        return 0;
    }
    let q = unsafe { slice::from_raw_parts(ptr, n as usize) };
    if feet_ok(q) {
        1
    } else {
        0
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn poly() {
        let s = [0i64, 1, 4, 9, 16, 25]; // squares -> degree 2
        assert_eq!(chiron_poly_degree(s.as_ptr(), s.len() as i32), 2);
    }
    #[test]
    fn feet() {
        // five dactyls + a spondee = a valid hexameter shape
        let q = [1u8,0,0, 1,0,0, 1,0,0, 1,0,0, 1,0,0, 1,1];
        assert!(feet_ok(&q));
        assert!(!feet_ok(&[1u8,0,0])); // only one foot
    }
}
