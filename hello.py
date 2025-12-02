def main():
    name = input("What is your name? ").strip()
    age = int(input(f"How old are you {name}? "))

    print(f"Hello {name}!")
    print(f"In 10 years you'll be {age + 10}")

    years = [age + i for i in range(11)]
    print(f"Next 10 years: {', '.join(map(str,years))}")

if __name__ == "__main__":
    main()