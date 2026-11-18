# Бот-помічник з адресною книгою та днями народження.
# Об'єднує попередні домашки: класи (hw-06), бот з декоратором (hw-05)
# і пошук найближчих днів народження (hw-03).

from collections import UserDict
from datetime import datetime, timedelta


# ---------- Класи адресної книги ----------

class Field:
    """Базовий клас для всіх полів запису."""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class Name(Field):
    """Ім'я контакту — обов'язкове поле."""

    def __init__(self, value):
        if not value:
            raise ValueError("Name is required.")
        super().__init__(value)


class Phone(Field):
    """Номер телефону — рівно 10 цифр."""

    def __init__(self, value):
        if not (value.isdigit() and len(value) == 10):
            raise ValueError("Phone number must contain exactly 10 digits.")
        super().__init__(value)


class Birthday(Field):
    """День народження у форматі DD.MM.YYYY. Зберігаємо як дату."""

    def __init__(self, value):
        try:
            # "15.03.1990" -> дата 1990-03-15
            date = datetime.strptime(value, "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")
        super().__init__(date)

    def __str__(self):
        # Показуємо дату в тому ж форматі, в якому її вводять
        return self.value.strftime("%d.%m.%Y")


class Record:
    """Один контакт: ім'я, список телефонів і (необов'язково) день народження."""

    def __init__(self, name):
        self.name = Name(name)
        self.phones = []
        self.birthday = None

    def add_phone(self, phone):
        if self.find_phone(phone):
            raise ValueError(f"Phone {phone} already exists.")
        self.phones.append(Phone(phone))

    def find_phone(self, phone):
        for p in self.phones:
            if p.value == phone:
                return p
        return None

    def remove_phone(self, phone):
        p = self.find_phone(phone)
        if p is None:
            raise ValueError(f"Phone {phone} not found.")
        self.phones.remove(p)

    def edit_phone(self, old_phone, new_phone):
        p = self.find_phone(old_phone)
        if p is None:
            raise ValueError(f"Phone {old_phone} not found.")
        new_p = Phone(new_phone)   # спершу перевіряємо новий номер
        index = self.phones.index(p)
        self.phones[index] = new_p

    def add_birthday(self, birthday):
        """Додає (або замінює) день народження — він може бути лише один."""
        self.birthday = Birthday(birthday)

    def __str__(self):
        phones = "; ".join(p.value for p in self.phones)
        text = f"Contact name: {self.name.value}, phones: {phones}"
        if self.birthday:
            text = text + f", birthday: {self.birthday}"
        return text


def get_birthday_in_year(birthday, year):
    """
    День народження в заданому році.
    29 лютого в невисокосний рік переносимо на 1 березня.
    """
    try:
        return birthday.replace(year=year)
    except ValueError:
        return birthday.replace(year=year, month=3, day=1)


class AddressBook(UserDict):
    """Адресна книга: ключ — ім'я, значення — Record."""

    def add_record(self, record):
        self.data[record.name.value] = record

    def find(self, name):
        return self.data.get(name)

    def delete(self, name):
        if name in self.data:
            del self.data[name]

    def get_upcoming_birthdays(self):
        """
        Повертає список {"name": ..., "congratulation_date": "DD.MM.YYYY"}
        для контактів, у яких день народження від сьогодні до +7 днів.
        Якщо він у суботу чи неділю — вітаємо в понеділок.
        (Функція з домашки hw-03, адаптована під AddressBook.)
        """
        today = datetime.today().date()
        upcoming = []

        for record in self.data.values():
            if record.birthday is None:
                continue   # у контакту немає дня народження — пропускаємо

            birthday = record.birthday.value
            birthday_this_year = get_birthday_in_year(birthday, today.year)
            if birthday_this_year < today:
                birthday_this_year = get_birthday_in_year(birthday, today.year + 1)

            days_left = (birthday_this_year - today).days

            if 0 <= days_left <= 7:
                congratulation_date = birthday_this_year
                if congratulation_date.weekday() == 5:      # субота
                    congratulation_date = congratulation_date + timedelta(days=2)
                elif congratulation_date.weekday() == 6:    # неділя
                    congratulation_date = congratulation_date + timedelta(days=1)

                upcoming.append({
                    "name": record.name.value,
                    "congratulation_date": congratulation_date.strftime("%d.%m.%Y"),
                })

        return upcoming


# ---------- Обробка помилок ----------

def input_error(func):
    """
    Декоратор: ловить помилки у функціях-обробниках,
    щоб бот не падав, а показував користувачу зрозуміле повідомлення.
    """
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            # Текст помилки вже зрозумілий: "Phone number must contain..." тощо
            return str(e)
        except IndexError:
            return "Enter user name."
        except KeyError:
            return "Contact not found."

    return inner


# ---------- Команди бота ----------

def parse_input(user_input):
    """Розбиває введений рядок на команду та аргументи."""
    cmd, *args = user_input.split()
    cmd = cmd.strip().lower()
    return cmd, *args


@input_error
def add_contact(args, book: AddressBook):
    """add [ім'я] [телефон] — новий контакт або ще один телефон до існуючого."""
    if len(args) < 2:
        raise ValueError("Give me name and phone please.")
    name, phone, *_ = args
    record = book.find(name)
    if record is None:
        record = Record(name)
        # Спершу додаємо телефон: якщо він неправильний, буде помилка
        # і порожній контакт не потрапить у книгу
        record.add_phone(phone)
        book.add_record(record)
        return "Contact added."
    record.add_phone(phone)
    return "Contact updated."


@input_error
def change_contact(args, book: AddressBook):
    """change [ім'я] [старий телефон] [новий телефон]."""
    if len(args) < 3:
        raise ValueError("Give me name, old phone and new phone please.")
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    record.edit_phone(old_phone, new_phone)
    return "Contact updated."


@input_error
def show_phone(args, book: AddressBook):
    """phone [ім'я] — показує всі телефони контакту."""
    name = args[0]                 # якщо ім'я не ввели — IndexError
    record = book.find(name)
    if record is None:
        raise KeyError
    if not record.phones:
        return f"{name} has no phones."
    return "; ".join(p.value for p in record.phones)


@input_error
def show_all(book: AddressBook):
    """all — показує всі контакти."""
    if not book.data:
        return "No contacts saved."
    lines = []
    for record in book.data.values():
        lines.append(str(record))
    return "\n".join(lines)


@input_error
def add_birthday(args, book: AddressBook):
    """add-birthday [ім'я] [DD.MM.YYYY]."""
    if len(args) < 2:
        raise ValueError("Give me name and birthday (DD.MM.YYYY) please.")
    name, birthday, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    record.add_birthday(birthday)
    return "Birthday added."


@input_error
def show_birthday(args, book: AddressBook):
    """show-birthday [ім'я]."""
    name = args[0]                 # якщо ім'я не ввели — IndexError
    record = book.find(name)
    if record is None:
        raise KeyError
    if record.birthday is None:
        return f"{name} has no birthday saved."
    return f"{name}: {record.birthday}"


@input_error
def birthdays(args, book: AddressBook):
    """birthdays — кого вітати протягом наступних 7 днів."""
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No birthdays in the next 7 days."
    lines = []
    for item in upcoming:
        lines.append(f"{item['name']}: {item['congratulation_date']}")
    return "\n".join(lines)


def main():
    book = AddressBook()
    print("Welcome to the assistant bot!")
    while True:
        user_input = input("Enter a command: ")

        # Порожній рядок — просто питаємо знову
        if not user_input.strip():
            continue

        command, *args = parse_input(user_input)

        if command in ["close", "exit"]:
            print("Good bye!")
            break

        elif command == "hello":
            print("How can I help you?")

        elif command == "add":
            print(add_contact(args, book))

        elif command == "change":
            print(change_contact(args, book))

        elif command == "phone":
            print(show_phone(args, book))

        elif command == "all":
            print(show_all(book))

        elif command == "add-birthday":
            print(add_birthday(args, book))

        elif command == "show-birthday":
            print(show_birthday(args, book))

        elif command == "birthdays":
            print(birthdays(args, book))

        else:
            print("Invalid command.")


if __name__ == "__main__":
    main()
