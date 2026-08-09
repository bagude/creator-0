def run(prog):
    st = []
    for ins in prog:
        op = ins[0]
        if op == "PUSH":
            st.append(ins[1])
        elif op == "ADD":
            if len(st) < 2:
                return "ERROR"
            st.append(st.pop() + st.pop())
        elif op == "DUP":
            if not st:
                return "ERROR"
            st.append(st[-1])
        elif op == "SWAP":
            if len(st) < 2:
                return "ERROR"
            st[-1], st[-2] = st[-2], st[-1]
        elif op == "POP":
            if not st:
                return "ERROR"
            st.pop()
    return st[-1] if st else "EMPTY"
