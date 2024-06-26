from app import db

class ParameterListeTest(db.Model):
    __tablename__ = 'parameterListeTest'
    ID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(88), unique=True)
    Synonyme = db.Column(db.String(120))
    EDV = db.Column(db.String(12))
    BereichID = db.Column(db.Integer, db.ForeignKey('parameterBereiche.ID'), nullable=False)  # Annahme eines Fremdschlüssels
    MaterialID = db.Column(db.Integer, db.ForeignKey('parameterMaterial.ID'), nullable=False)  # Annahme eines Fremdschlüssels
    MethodeID = db.Column(db.Integer, db.ForeignKey('parameterMethoden.ID'), nullable=False)  # Annahme eines Fremdschlüssels
    goae = db.Column(db.String(28))
    Punkte = db.Column(db.Integer, nullable=False)
    goaeSingle = db.Column(db.Integer)
    Zeitstempel = db.Column(db.TIMESTAMP, nullable=False)
    Hauptparameter = db.Column(db.String(90))
    Parameterzusatz = db.Column(db.String(90))

    # Beziehungen
    Bereich = db.relationship('ParameterBereiche', backref='parameterListeTest')
    Material = db.relationship('ParameterMaterial', backref='parameterListeTest')
    Methode = db.relationship('ParameterMethoden', backref='parameterListeTest')

class ParameterBereiche(db.Model):
    __tablename__ = 'parameterBereiche'
    ID = db.Column(db.Integer, primary_key=True)
    Bereich = db.Column(db.String(60), nullable=False, unique=True)

class ParameterMaterial(db.Model):
    __tablename__ = 'parameterMaterial'
    ID = db.Column(db.Integer, primary_key=True)
    Material = db.Column(db.String(60), nullable=False, unique=True)

    def to_dict(self):
        return {
            "Material": self.Material
        }

class ParameterMethoden(db.Model):
    __tablename__ = 'parameterMethoden'
    ID = db.Column(db.Integer, primary_key=True)
    Methode = db.Column(db.String(60), nullable=False, unique=True)


class ProjektListeTest(db.Model):
    __tablename__ = 'projektListeTest'
    ID = db.Column(db.Integer, primary_key=True)
    AuftragsID = db.Column(db.String(12), nullable=False)
    AuftraggeberID = db.Column(db.Integer, db.ForeignKey('projektAuftraggeber.ID'), nullable=False)
    Angebotsdatum = db.Column(db.String(7), nullable=False)  # Format JJJJ-MM
    AnbieterID = db.Column(db.Integer, db.ForeignKey('projektAnbieter.ID'), nullable=False)
    Standort = db.Column(db.String(30), nullable=False)
    Bemerkung = db.Column(db.String(40), nullable=False)
    Zeitstempel = db.Column(db.TIMESTAMP)

    # Beziehungen zu anderen Tabellen
    Auftraggeber = db.relationship("ProjektAuftraggeber", backref='projektListeTest')
    Anbieter = db.relationship("ProjektAnbieter", backref='projektListeTest')
    projektBefundpreise = db.relationship('ProjektBefundpreiseTest', backref='ProjektListeTest')

    def to_dict(self):
        return {
            'ID': self.ID,
            'AuftragsID': self.AuftragsID,
            'Angebotsdatum': self.Angebotsdatum,
            'Standort': self.Standort,
            'Bemerkung': self.Bemerkung,
            'Zeitstempel': self.Zeitstempel,  # Zeitstempel in String konvertieren
            'Auftraggeber': {
                'ID': self.Auftraggeber.ID,
                'Auftraggeber': self.Auftraggeber.Auftraggeber
            } if self.Auftraggeber else {},  # Verknüpfte Daten von Auftraggeber
            'Anbieter': {
                'ID': self.Anbieter.ID,
                'Anbieter': self.Anbieter.Anbieter
            } if self.Anbieter else {},  # Verknüpfte Daten von Anbieter
            'Befundmengen': sum(befundpreis.Leistungen for befundpreis in self.projektBefundpreise)
        }

class ProjektAuftraggeber(db.Model):
    __tablename__ = 'projektAuftraggeber'
    ID = db.Column(db.Integer, primary_key=True)
    Auftraggeber = db.Column(db.String(60), nullable=False , unique=True)
    def to_dict(self):
        return {
            "Auftraggeber": self.Auftraggeber
        }

class ProjektAnbieter(db.Model):
    __tablename__ = 'projektAnbieter'
    ID = db.Column(db.Integer, primary_key=True)
    Anbieter = db.Column(db.String(60), nullable=False, unique=True)
    def to_dict(self):
        return {
            "Anbieter": self.Anbieter
        }

class GeraeteListe(db.Model):
    __tablename__ = 'geraeteListe'

    ID = db.Column(db.Integer, primary_key=True)
    VertreiberID = db.Column(db.Integer, db.ForeignKey('geraeteVertreiber.ID'), nullable=False)
    GeraeteartID = db.Column(db.Integer, nullable=False)
    Geraetebezeichnung = db.Column(db.String(50), nullable=False, unique=True)
    Bereich = db.Column(db.String(40), nullable=False)
    Zeitstempel = db.Column(db.TIMESTAMP, nullable=False)

    # Beziehung zu gerateVertreiber
    Vertreiber = db.relationship('GeraeteVertreiber', backref='geraeteListe')

class GeraeteVertreiber(db.Model):
    __tablename__ = 'geraeteVertreiber'
    ID = db.Column(db.Integer, primary_key=True)
    Vertreiber = db.Column(db.String(60), nullable=False , unique=True)

class ProjektBefundpreiseTest(db.Model):
    __tablename__ = 'projektBefundpreiseTest'

    ID = db.Column(db.Integer, primary_key=True)
    ProjektID = db.Column(db.Integer, db.ForeignKey('projektListeTest.ID'), nullable=False)
    AnbieterID = db.Column(db.Integer, db.ForeignKey('projektAnbieter.ID'), nullable=False)
    ParameterID = db.Column(db.Integer, db.ForeignKey('parameterListeTest.ID'), nullable=False)
    Leistungen = db.Column(db.Integer, nullable=False)
    PpBReagenz = db.Column(db.Float, nullable=False)
    PpBKontrollen = db.Column(db.Float, nullable=False)
    Zeitstempel = db.Column(db.TIMESTAMP, nullable=False)

    # Beziehungen zu anderen Tabellen
    Projekt = db.relationship('ProjektListeTest', backref='projektBefundpreiseTest')
    Anbieter = db.relationship('ProjektAnbieter', backref='projektBefundpreiseTest')
    Parameter = db.relationship('ParameterListeTest', backref='projektBefundpreiseTest')

