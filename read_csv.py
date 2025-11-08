import csv
import pandas


# Converts XLS files into JSON files

# df = pandas.read_excel("./NATIONAL SIDDHA MORBIDITY CODES.xls")
# df.to_csv("Siddha.csv", index=False)


with open("./Data/Siddha.csv") as file:
    csv_reader = csv.DictReader(file)

    for line in csv_reader:
        print(line["NAMC_CODE"])

