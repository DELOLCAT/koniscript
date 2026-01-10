func loop(n) {
    if (n == 0) {
        return 0
    }
    return loop(n - 1)
}
loop(10000)