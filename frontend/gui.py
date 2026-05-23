import tkinter as tk
from tkinter import messagebox, filedialog
import os
import glob
from typing import Iterator, List, Optional
from backend.flashcard import Flashcard
from backend.csvHandler import loadFlashcards, saveFlashcards
from backend.sessionProvider import SessionProvider


BACKGROUND_COLOR: str = "#B1DDC6"


class MainWindow(tk.Tk):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.title("Flash Card App")
        self.geometry("900x800")
        self.config(padx=20, pady=20)

        self.welcome_frame = tk.Frame(self)
        self.welcome_frame.pack(expand=True)

        self.welcome = tk.Label(self.welcome_frame, text="Welcome to the Flashcard app.\nPlease select a deck to start.", font=("Arial", 16))
        self.welcome.pack(pady=20)

        # --- File selection ---
        self.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))

        listbox_frame = tk.Frame(self.welcome_frame)
        listbox_frame.pack(pady=10)

        scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL)
        self.csv_listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, height=10)
        scrollbar.config(command=self.csv_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.csv_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.status_label = tk.Label(self.welcome_frame, text="")
        self.status_label.pack(pady=5)

        # --- Load CSV files ---
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        search_pattern = os.path.join(self.data_dir, "*.csv")
        csv_files = glob.glob(search_pattern)

        if not csv_files:
            self.status_label.config(text=f"No CSV files found in: {self.data_dir}")
            messagebox.showwarning("No CSV Files Found", f"No CSV files were found in {self.data_dir}.\nPlease add some flashcard decks (.csv) to this directory.")
        else:
            for file_path in csv_files:
                file_name = os.path.basename(file_path)
                self.csv_listbox.insert(tk.END, file_name)
            self.status_label.config(text=f"Found {len(csv_files)} CSV files. Select one and press Start.")

        self.startButton = tk.Button(self.welcome_frame, text="Start", width=25, command=self.launchFlashcards)
        self.startButton.pack(pady=20)

        # --- Session variables ---
        self.csv_file_path: Optional[str] = None
        self.frontTextId: Optional[int] = None
        self.backTextId: Optional[int] = None
        self.flashcards: List[Flashcard] = []
        self.sessionProvider: Optional[SessionProvider] = None
        self.flashcardGenerator: Optional[Iterator[Flashcard]] = None
        self.currentCard: Optional[Flashcard] = None


    def launchFlashcards(self) -> None:
        selection_indices = self.csv_listbox.curselection()
        if not selection_indices:
            messagebox.showwarning("No Selection", "Please select a CSV file to start.")
            return

        selected_file_name = self.csv_listbox.get(selection_indices[0])
        self.csv_file_path = os.path.join(self.data_dir, selected_file_name)

        self.title(selected_file_name)
        self.welcome_frame.pack_forget()
        self.configure(bg=BACKGROUND_COLOR, padx=50, pady=50)

        self.flashcards = loadFlashcards(self.csv_file_path)
        self.sessionProvider: SessionProvider = SessionProvider(self.flashcards)
        self.flashcardGenerator: Iterator[Flashcard] = self.sessionProvider.startSession()
        self.createWidgets()
        self.nextFlashcard()

    def createWidgets(self) -> None:
        gui_dir = os.path.dirname(__file__)
        self.canvas = tk.Canvas(self, width=800, height=600)
        self.cardFrontImage = tk.PhotoImage(file=os.path.join(gui_dir, 'images', 'cardFront.png'))
        self.cardBackImage = tk.PhotoImage(file=os.path.join(gui_dir, 'images', 'cardBack.png'))
        self.canvasImage = self.canvas.create_image(400, 263, image=self.cardFrontImage)
        self.frontTextId = self.canvas.create_text(400, 140, text="", fill="black", font=("Arial", 60, "bold"))
        self.backTextId = self.canvas.create_text(400, 263, text="", fill="black", font=("Arial", 36, "normal"))
        self.canvas.configure(bg=BACKGROUND_COLOR, highlightthickness=0)
        self.canvas.grid(row=0, column=0, columnspan=2)

        self.crossImage = tk.PhotoImage(file=os.path.join(gui_dir, 'images', 'wrong.png'))
        self.wrongButton = tk.Button(image=self.crossImage, highlightthickness=0, command=self.onWrong)
        self.wrongButton.grid(row=1, column=0)

        self.tickImage = tk.PhotoImage(file=os.path.join(gui_dir, 'images', 'right.png'))
        self.rightButton = tk.Button(image=self.tickImage, highlightthickness=0, command=self.onRight)
        self.rightButton.grid(row=1, column=1)

    def nextFlashcard(self):
        try:
            self.currentCard = next(self.flashcardGenerator)
            self.showFront()
        except StopIteration:
            self.endSession()

    def showFront(self):
        frontText = f"\n\nAtomic Name & Number?"
        self.canvas.itemconfig(self.frontTextId, text=self.currentCard.front)
        self.canvas.itemconfig(self.backTextId, text=frontText)
        self.canvas.itemconfig(self.canvasImage, image=self.cardFrontImage)
        self.wrongButton.grid_forget()
        self.rightButton.grid_forget()
        self.canvas.bind("<Button-1>", self.showBack)

    def showBack(self, event=None):
        self.canvas.unbind("<Button-1>")
        backFirst = self.currentCard.back.split('|')[1]
        backNext = self.currentCard.back.split('|')[0]
        backText = f"\n\nName: {backFirst}\n\nAtomic Number: {backNext}"
        self.canvas.itemconfig(self.backTextId, text=backText)
        self.canvas.itemconfig(self.canvasImage, image=self.cardBackImage)
        self.wrongButton.grid(row=1, column=0)
        self.rightButton.grid(row=1, column=1)

    def onRight(self):
        self.sessionProvider.processResponse(self.currentCard, 'right')
        self.nextFlashcard()

    def onWrong(self):
        self.sessionProvider.processResponse(self.currentCard, 'wrong')
        self.nextFlashcard()

    def endSession(self):
        self.sessionProvider.endSession()
        #next_review_date = min(card.nextReviewDate for card in self.flashcards)
        #messagebox.showinfo("Session End", f"The next review date is: {next_review_date}")
        if self.csv_file_path:
            saveFlashcards(self.flashcards, self.csv_file_path)
        self.destroy()
