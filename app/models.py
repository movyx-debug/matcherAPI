
from app import db

class ParameterListe(db.Model):
    __tablename__ = 'parameterListe'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(88))
    synonyme = db.Column(db.String(120))
    edv = db.Column(db.String(12))
    bereich_id = db.Column(db.Integer, db.ForeignKey('bereich.id'), nullable=False)  # Annahme eines Fremdschlüssels
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)  # Annahme eines Fremdschlüssels
    methode_id = db.Column(db.Integer, db.ForeignKey('methode.id'), nullable=False)  # Annahme eines Fremdschlüssels
    goae = db.Column(db.String(28))
    punkte = db.Column(db.Integer, nullable=False)
    goae_single = db.Column(db.Integer)
    zeitstempel = db.Column(db.TIMESTAMP, nullable=False, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Beziehungen
    bereich = db.relationship('Bereich', backref='parameter')
    material = db.relationship('Material', backref='parameter')
    methode = db.relationship('Methode', backref='parameter')
