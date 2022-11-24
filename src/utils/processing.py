def text2num(text:str) -> int:
    last_letter = text[-1]
    num = float(text[:-1])
    
    if last_letter in ["k", "K"]: num *= (10**3)
    if last_letter in ["m", "M"]: num *= (10**6)
    if last_letter in ["b", "B"]: num *= (10**9)

    return num

class US:
    def __init__(self):
        self.state_names = ["NY"]
        
if __name__ == "__main__":
    print(US().state_names)